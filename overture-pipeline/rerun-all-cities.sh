#!/usr/bin/env bash
# =============================================================================
# Re-run the Overture pipeline for Brisbane, Sydney, and Melbourne after the
# numpy-array parser fix. Uploads fresh outputs to s3://unsw-cse-cruiser-overture.
#
# Safe to re-run: overwrites deterministic S3 keys, preserves cached GEE
# satellite embeddings so only the Overture work is redone.
#
# Usage (on EC2, inside tmux so disconnects don't kill it):
#   tmux new -s rerun
#   cd ~/cruiser-dashboard/overture-pipeline
#   chmod +x rerun-all-cities.sh
#   ./rerun-all-cities.sh
#   # Ctrl-b then d to detach; `tmux attach -t rerun` to reattach
# =============================================================================
set -euo pipefail

cd "$(dirname "$0")"

echo "[1/4] Pulling latest fix from git..."
git pull

echo ""
echo "[2/4] Activating virtualenv..."
source .venv/bin/activate

echo ""
echo "[3/4] Clearing stale Overture outputs (keeping cached satellite embeddings)..."
for city in brisbane sydney melbourne; do
    rm -rf "data/${city}/overture_releases"
done

CITIES=(
    "brisbane 11677792"
    "sydney 5750005"
    "melbourne 4246124"
)

echo ""
echo "[4/4] Running pipeline for each city..."
START=$(date +%s)

for pair in "${CITIES[@]}"; do
    read -r city rel <<< "$pair"
    echo ""
    echo "=========================================="
    echo "  ${city} (relation ${rel})"
    echo "=========================================="
    python download_multi_release.py \
        --city "$city" \
        --relation-id "$rel" \
        --satellite \
        --ee-project datacruiser \
        --h3-resolution 9 \
        --upload-s3 \
        2>&1 | tee "${city}-rerun.log"
done

ELAPSED=$(( $(date +%s) - START ))

echo ""
echo "=========================================="
echo "  Done in $((ELAPSED / 60))m $((ELAPSED % 60))s"
echo "=========================================="
echo ""
echo "S3 contents for each city:"
for pair in "${CITIES[@]}"; do
    read -r city _ <<< "$pair"
    echo ""
    echo "--- ${city} ---"
    aws s3 ls "s3://unsw-cse-cruiser-overture/processed/overture/${city}/2026-02-18.0/" \
        --human-readable
done

echo ""
echo "Quick sanity check (speed columns in Brisbane combined parquet):"
python -c "import pandas as pd; df = pd.read_parquet('data/brisbane/overture_releases/2026-02-18.0/combined_res09.parquet'); cols = [c for c in df.columns if 'speed' in c.lower()]; print('speed cols:', cols); print(df[cols].describe())"
