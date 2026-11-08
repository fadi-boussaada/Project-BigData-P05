#!/usr/bin/env python3
"""P05 - Semaine 1 : retrouver les lignes rejetees par l'audit (timestamp d'unite inconnue
ou autre motif de rejet) pour les citer dans le journal de rejets.

Memes regles que 02_audit_schema.py. Le champ user_id est MASQUE dans la sortie.

Usage : python3 scripts/04_find_rejected.py data/raw/Appliances.jsonl.gz --out reports/rejected_rows.json
"""
import argparse, gzip, json, os, sys, datetime as dt

def opener(path):
    return gzip.open(path, "rt", encoding="utf-8", errors="replace") if path.endswith(".gz") \
        else open(path, "rt", encoding="utf-8", errors="replace")

def infer_unit(ts):
    if ts >= 1e11: return "ms"
    if 1e9 <= ts < 1e10: return "s"
    return "inconnu"

def reason(r):
    if not isinstance(r, dict): return "json_invalide"
    if not r.get("parent_asin") or not isinstance(r.get("parent_asin"), str): return "parent_asin_absent"
    rt = r.get("rating")
    if not isinstance(rt, (int, float)) or isinstance(rt, bool) or not (1 <= rt <= 5): return "rating_hors_[1,5]_ou_absent"
    ts = r.get("timestamp")
    if not isinstance(ts, (int, float)) or isinstance(ts, bool) or ts <= 0: return "timestamp_absent_ou_invalide"
    if infer_unit(ts) == "inconnu": return "timestamp_unite_inconnue"
    txt = r.get("text") if isinstance(r.get("text"), str) else ""
    ttl = r.get("title") if isinstance(r.get("title"), str) else ""
    if not txt.strip() and not ttl.strip(): return "texte_et_titre_vides"
    return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--out", default="reports/rejected_rows.json")
    a = ap.parse_args()

    rejected = []
    n = 0
    with opener(a.path) as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line: continue
            n += 1
            try:
                r = json.loads(line)
            except Exception:
                rejected.append({"line_number": lineno, "reason": "json_invalide", "raw_start": line[:200]})
                continue
            why = reason(r)
            if why:
                row = {k: (v if k != "user_id" else "<masque>") for k, v in r.items() if k != "images"}
                if isinstance(row.get("text"), str) and len(row["text"]) > 300:
                    row["text"] = row["text"][:300] + "..."
                info = {"line_number": lineno, "reason": why, "row": row}
                ts = r.get("timestamp")
                if isinstance(ts, (int, float)) and not isinstance(ts, bool) and ts > 0:
                    for div in (1, 1000):
                        try:
                            info[f"interprete_si_{'secondes' if div == 1 else 'millisecondes'}"] = \
                                dt.datetime.fromtimestamp(ts / div, dt.timezone.utc).isoformat()
                        except Exception:
                            info[f"interprete_si_{'secondes' if div == 1 else 'millisecondes'}"] = "hors plage"
                rejected.append(info)

    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump({"file": a.path, "lines_read": n, "rejected_count": len(rejected), "rejected": rejected},
                  f, indent=2, ensure_ascii=False)
    print(f"Lignes lues : {n} | rejetees : {len(rejected)}")
    for r in rejected:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    print(f"Rapport : {a.out}")

if __name__ == "__main__":
    sys.exit(main())