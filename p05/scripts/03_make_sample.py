#!/usr/bin/env python3
"""P05 - Semaine 1 : echantillon deterministe, par PRODUIT (parent_asin).

Pourquoi par produit ? Le "document" TF-IDF = tous les avis d'un produit (cdc 6.3).
Echantillonner des avis au hasard couperait les produits en morceaux et fausserait
TF et DF. On garde donc TOUS les avis des produits retenus.

Regle (stable, rejouable, independante de l'ordre des lignes) :
    keep(parent_asin) <=>  blake2b(salt + parent_asin) mod 10000  <  rate * 10000

Les lignes retenues sont recopiees telles quelles (JSON brut) ; seules les lignes
au JSON invalide ou sans parent_asin sont ignorees (comptees dans le manifeste).

Usage : python3 scripts/03_make_sample.py data/raw/Appliances.jsonl.gz \
            --rate 0.01 --salt p05-v1 --out data/samples/dev_1pct.jsonl.gz
"""
import argparse, collections, gzip, hashlib, json, os, sys, datetime as dt

def opener(path, mode="rt"):
    return gzip.open(path, mode, encoding="utf-8") if path.endswith(".gz") else open(path, mode, encoding="utf-8")

def bucket(salt: str, pa: str) -> int:
    d = hashlib.blake2b((salt + "|" + pa).encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(d, "big") % 10000

def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""): h.update(chunk)
    return h.hexdigest()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--rate", type=float, required=True, help="fraction de PRODUITS retenus, ex 0.01")
    ap.add_argument("--salt", default="p05-v1")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    thr = int(a.rate * 10000)

    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    read = kept = skipped_invalid = 0
    prod_all, prod_kept = set(), set()
    with opener(a.path) as fin, opener(a.out, "wt") as fout:
        for line in fin:
            line = line.strip()
            if not line: continue
            read += 1
            try:
                pa = json.loads(line).get("parent_asin")
            except Exception:
                pa = None
            if not pa:
                skipped_invalid += 1; continue
            prod_all.add(pa)
            if bucket(a.salt, pa) < thr:
                fout.write(line + "\n"); kept += 1; prod_kept.add(pa)

    manifest = {
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "input": a.path, "output": a.out,
        "rule": f"blake2b(salt|parent_asin) mod 10000 < {thr}", "salt": a.salt, "rate_products": a.rate,
        "lines_read": read, "lines_skipped_invalid_or_no_parent_asin": skipped_invalid,
        "reviews_kept": kept, "reviews_retention": round(kept / max(read, 1), 5),
        "products_total_seen": len(prod_all), "products_kept": len(prod_kept),
        "products_retention": round(len(prod_kept) / max(len(prod_all), 1), 5),
        "output_sha256": sha256_file(a.out),
        "note": "Deduplication non appliquee ici (cf. S2, cle technique d'avis).",
    }
    mpath = a.out.replace(".jsonl.gz", "").replace(".jsonl", "") + ".manifest.json"
    with open(mpath, "w", encoding="utf-8") as f: json.dump(manifest, f, indent=2)
    print(json.dumps(manifest, indent=2))

if __name__ == "__main__":
    sys.exit(main())
