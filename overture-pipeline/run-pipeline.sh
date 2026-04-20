#!/usr/bin/env bash
# =============================================================================
# Run the full Overture pipeline for a city: extract → aggregate → upload to S3.
#
# Usage:
#   ./run-pipeline.sh <city> <relation-id> [extra pipeline args...]
#
# Examples:
#   # Basic (extract + hex aggregation + upload)
#   ./run-pipeline.sh sydney 5750005 --hex-agg
#
#   # With satellite embeddings
#   ./run-pipeline.sh sydney 5750005 --satellite --ee-project datacruiser
#
#   # Melbourne
#   ./run-pipeline.sh melbourne 4246124 --satellite --ee-project datacruiser
#
#   # Custom data directory (e.g., larger EBS volume)
#   ./run-pipeline.sh sydney 5750005 --hex-agg --data-dir /mnt/data
# =============================================================================
set -euo pipefail

if [ $# -lt 2 ]; then
    echo "Usage: $0 <city> <relation-id> [extra pipeline args...]"
    echo ""
    echo "Examples:"
    echo "  $0 sydney 5750005 --hex-agg"
    echo "  $0 sydney 5750005 --satellite --ee-project datacruiser"
    echo "  $0 melbourne 4246124 --satellite --ee-project datacruiser"
    exit 1
fi

CITY="$1"
RELATION_ID="$2"
shift 2

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Activate virtualenv if it exists
if [ -f .venv/bin/activate ]; then
    source .venv/bin/activate
fi

# Defaults
RELEASE="2026-02-18.0"
H3_RES=9
DATA_DIR="./data"

# Detect flags from extra args
HAS_SATELLITE=false
for arg in "$@"; do
    if [ "$arg" = "--satellite" ]; then
        HAS_SATELLITE=true
    fi
done

# Extract --data-dir and --h3-resolution if provided
EXTRA_ARGS=("$@")
for i in "${!EXTRA_ARGS[@]}"; do
    if [ "${EXTRA_ARGS[$i]}" = "--data-dir" ] && [ $((i + 1)) -lt ${#EXTRA_ARGS[@]} ]; then
        DATA_DIR="${EXTRA_ARGS[$((i + 1))]}"
    fi
    if [ "${EXTRA_ARGS[$i]}" = "--h3-resolution" ] && [ $((i + 1)) -lt ${#EXTRA_ARGS[@]} ]; then
        H3_RES="${EXTRA_ARGS[$((i + 1))]}"
    fi
done

echo "============================================"
echo "  Overture Pipeline — ${CITY}"
echo "============================================"
echo "  City:        ${CITY}"
echo "  Relation ID: ${RELATION_ID}"
echo "  Release:     ${RELEASE}"
echo "  H3 Res:      ${H3_RES}"
echo "  Satellite:   ${HAS_SATELLITE}"
echo "  Data Dir:    ${DATA_DIR}"
echo "============================================"
echo ""

# --------------------------------------------------------------------------
# Step 1: Run the pipeline
# --------------------------------------------------------------------------
echo "[Step 1] Running download_multi_release.py ..."
echo ""

python download_multi_release.py \
    --city "$CITY" \
    --relation-id "$RELATION_ID" \
    --data-dir "$DATA_DIR" \
    "$@"

echo ""
echo "[Step 1] Pipeline complete."
echo ""

# --------------------------------------------------------------------------
# Step 2: Upload to S3
# --------------------------------------------------------------------------
echo "[Step 2] Uploading to S3 ..."
echo ""

UPLOAD_ARGS=(
    --city "$CITY"
    --release "$RELEASE"
    --h3-resolution "$H3_RES"
    --data-dir "$DATA_DIR"
)

if [ "$HAS_SATELLITE" = true ]; then
    UPLOAD_ARGS+=(--include-satellite)
fi

python upload_to_s3.py "${UPLOAD_ARGS[@]}"

echo ""
echo "============================================"
echo "  Pipeline complete for ${CITY}!"
echo "============================================"
echo ""
echo "Next steps:"
echo "  1. Run 'npm run scrape' on the dashboard to update metadata"
echo "  2. Dashboard will auto-refresh within 5 minutes"
echo ""
