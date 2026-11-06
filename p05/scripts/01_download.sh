#!/usr/bin/env bash
# P05 - Semaine 1 : telechargement + manifeste de provenance (zone bronze locale)
# Usage : bash scripts/01_download.sh [dossier_sortie]
set -euo pipefail

OUT="${1:-data/raw}"
BASE="https://mcauleylab.ucsd.edu/public_datasets/data/amazon_2023/raw"
FILES=(
  "review_categories/Appliances.jsonl.gz"   # obligatoire
  "meta_categories/meta_Appliances.jsonl.gz" # facultatif mais recommande
)

mkdir -p "$OUT"
MANIFEST="$OUT/MANIFEST_download.json"
echo "[" > "$MANIFEST"
first=1
for f in "${FILES[@]}"; do
  name=$(basename "$f")
  url="$BASE/$f"
  echo ">> $url"
  # -C - : reprise possible ; -f : echec si HTTP >= 400 ; -L : suit les redirections
  curl -fL -C - --retry 3 -o "$OUT/$name" "$url" || { echo "!! echec pour $name (lien/acces a verifier)"; continue; }
  size=$(stat -c %s "$OUT/$name" 2>/dev/null || stat -f %z "$OUT/$name")
  sha=$(sha256sum "$OUT/$name" 2>/dev/null | cut -d' ' -f1 || shasum -a 256 "$OUT/$name" | cut -d' ' -f1)
  gzip -t "$OUT/$name" && integrity="gzip_ok" || integrity="gzip_CORROMPU"
  [ $first -eq 0 ] && echo "," >> "$MANIFEST"
  first=0
  cat >> "$MANIFEST" <<EOF
  {"file": "$name", "url": "$url", "downloaded_utc": "$(date -u +%FT%TZ)",
   "size_bytes": $size, "sha256": "$sha", "integrity": "$integrity"}
EOF
done
echo "]" >> "$MANIFEST"
echo "Manifeste ecrit : $MANIFEST"
