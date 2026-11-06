# P05 — Semaine 1 : cadrage, audit de schéma, échantillon témoin

Prérequis : Python ≥ 3.8 (bibliothèque standard uniquement), `curl`, `gzip`.

```bash
# 1. Télécharger les données réelles + manifeste de provenance
bash scripts/01_download.sh data/raw

# 2. Auditer le schéma effectif (≈ 2,1 M lignes, streaming). Collez le résultat dans la note de cadrage §3
python3 scripts/02_audit_schema.py data/raw/Appliances.jsonl.gz --out reports/audit_schema.json

# 3. Échantillons déterministes par produit (L1 ≈ 1 %, L2 ≈ 10 %)
python3 scripts/03_make_sample.py data/raw/Appliances.jsonl.gz --rate 0.01 --salt p05-v1 --out data/samples/dev_1pct.jsonl.gz
python3 scripts/03_make_sample.py data/raw/Appliances.jsonl.gz --rate 0.10 --salt p05-v1 --out data/samples/val_10pct.jsonl.gz

# Test sur le jeu jouet inventé (aucune donnée réelle)
python3 scripts/02_audit_schema.py data/toy/toy_reviews.jsonl.gz --out reports/audit_toy.json
```

Structure : `scripts/` · `data/toy/` (jeu jouet fictif, `TOY_*`) · `data/raw/` et `data/samples/` (non versionnés, ajouter au `.gitignore`) · `reports/` · `docs/note_de_cadrage.md`.

Ne jamais commiter `data/raw/`. Ne jamais afficher `user_id`.
