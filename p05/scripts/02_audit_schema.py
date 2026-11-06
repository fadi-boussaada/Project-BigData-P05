#!/usr/bin/env python3
"""P05 - Semaine 1 : audit du schema effectif d'un fichier JSONL(.gz) d'avis.

Lecture en streaming (memoire bornee). Produit un rapport JSON + un resume lisible.
Objectifs : champs presents/types, motifs de rejet (cf. cahier des charges 6.4),
unite reelle du timestamp (secondes vs millisecondes), plage de dates, notes,
nombre de produits, doublons potentiels, longueur des textes.

Usage : python3 scripts/02_audit_schema.py data/raw/Appliances.jsonl.gz --out reports/audit_schema.json
        (--max-lines N pour un audit partiel rapide ; attention : biais d'ordre !)
"""
import argparse, collections, datetime as dt, gzip, hashlib, json, statistics, sys

def opener(path):
    return gzip.open(path, "rt", encoding="utf-8", errors="replace") if path.endswith(".gz") \
        else open(path, "rt", encoding="utf-8", errors="replace")

def h8(s: str) -> bytes:
    return hashlib.blake2b(s.encode("utf-8", "replace"), digest_size=8).digest()

def infer_unit(ts):
    """Heuristique sur la magnitude. >1e12 : ms ; 1e9..1e11 : s ; sinon inconnu."""
    if ts >= 1e12: return "ms"
    if 1e9 <= ts < 1e11: return "s"
    return "inconnu"

def to_dt(ts, unit):
    return dt.datetime.fromtimestamp(ts / (1000 if unit == "ms" else 1), dt.timezone.utc)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--out", default="reports/audit_schema.json")
    ap.add_argument("--max-lines", type=int, default=0)
    a = ap.parse_args()

    n = 0
    key_present = collections.Counter()
    key_types = collections.defaultdict(collections.Counter)
    rejects = collections.Counter()
    ratings = collections.Counter()
    verified = collections.Counter()
    units = collections.Counter()
    products = set()
    seen = set(); dup = 0
    ts_valid = []
    text_len = []
    helpful_neg = 0

    with opener(a.path) as fh:
        for line in fh:
            if a.max_lines and n >= a.max_lines: break
            n += 1
            line = line.strip()
            if not line:
                rejects["ligne_vide"] += 1; continue
            try:
                r = json.loads(line)
                if not isinstance(r, dict): raise ValueError
            except Exception:
                rejects["json_invalide"] += 1; continue

            for k, v in r.items():
                key_present[k] += 1
                key_types[k][type(v).__name__] += 1

            bad = False
            pa = r.get("parent_asin")
            if not pa or not isinstance(pa, str):
                rejects["parent_asin_absent"] += 1; bad = True
            rt = r.get("rating")
            if not isinstance(rt, (int, float)) or isinstance(rt, bool) or not (1 <= rt <= 5):
                rejects["rating_hors_[1,5]_ou_absent"] += 1; bad = True
            else:
                ratings[float(rt)] += 1
            ts = r.get("timestamp")
            if not isinstance(ts, (int, float)) or isinstance(ts, bool) or ts <= 0:
                rejects["timestamp_absent_ou_invalide"] += 1; bad = True
            else:
                u = infer_unit(ts); units[u] += 1
                if u == "inconnu":
                    rejects["timestamp_unite_inconnue"] += 1; bad = True
            txt = (r.get("text") or "").strip() if isinstance(r.get("text"), str) else ""
            ttl = (r.get("title") or "").strip() if isinstance(r.get("title"), str) else ""
            if not txt and not ttl:
                rejects["texte_et_titre_vides"] += 1; bad = True
            elif not txt:
                rejects["text_vide_(titre_seul)_info"] += 0  # info, pas un rejet
            if bad: continue

            products.add(pa)
            text_len.append(len(txt))
            verified[str(r.get("verified_purchase"))] += 1
            if isinstance(r.get("helpful_vote"), (int, float)) and r["helpful_vote"] < 0: helpful_neg += 1
            ts_valid.append((ts, infer_unit(ts)))
            # cle technique de dedoublonnage candidate (regle publique, cf. note de cadrage)
            k = h8(f"{r.get('user_id')}|{pa}|{r.get('asin')}|{ts}|{txt}")
            if k in seen: dup += 1
            else: seen.add(k)

    valid = n - sum(v for k, v in rejects.items() if not k.endswith("_info"))
    report = {
        "file": a.path, "lines_read": n, "partial_audit": bool(a.max_lines),
        "valid_reviews_estimate": valid,
        "rejects_by_reason": dict(rejects),
        "fields_present": {k: {"count": c, "pct": round(100 * c / max(n, 1), 2),
                               "types": dict(key_types[k])} for k, c in sorted(key_present.items())},
        "ratings_distribution": {str(k): v for k, v in sorted(ratings.items())},
        "verified_purchase": dict(verified),
        "timestamp_unit_counts": dict(units),
        "distinct_parent_asin_valid": len(products),
        "duplicates_by_candidate_key": dup,
        "helpful_vote_negative": helpful_neg,
    }
    if ts_valid:
        mn, mx = min(ts_valid), max(ts_valid)
        report["date_range_utc"] = {"min": to_dt(*mn).isoformat(), "max": to_dt(*mx).isoformat(),
                                    "min_raw": mn[0], "max_raw": mx[0]}
    if text_len:
        s = sorted(text_len)
        report["text_length_chars"] = {"mean": round(statistics.mean(s), 1), "median": s[len(s) // 2],
                                       "p95": s[int(len(s) * .95) - 1 if len(s) > 20 else -1], "max": s[-1],
                                       "empty_text_count": sum(1 for x in s if x == 0)}

    import os
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"Lignes lues      : {n}")
    print(f"Avis valides (~) : {valid}  | produits distincts : {len(products)}")
    print(f"Rejets           : {dict(rejects) or 'aucun'}")
    print(f"Unite timestamp  : {dict(units)}")
    if "date_range_utc" in report: print(f"Plage de dates   : {report['date_range_utc']['min']} -> {report['date_range_utc']['max']}")
    print(f"Doublons (cle)   : {dup}")
    print(f"Rapport complet  : {a.out}")

if __name__ == "__main__":
    sys.exit(main())
