#!/usr/bin/env bash
# =============================================================================
# EC2 Setup Script for Overture Maps Pipeline
#
# Installs system dependencies, creates a Python virtualenv, and installs
# all required packages for download_multi_release.py and upload_to_s3.py.
#
# Supports Amazon Linux 2023 (dnf) and Ubuntu/Debian (apt) — auto-detected.
#
# Recommended EC2 instance: r6i.xlarge (4 vCPU, 32 GB RAM) or larger.
# Storage: 50+ GB EBS (gp3) for intermediate data.
# IAM: Attach a role with s3:PutObject/GetObject/ListBucket on datacruiser-stdb.
#
# Usage:
#   chmod +x ec2-setup.sh
#   ./ec2-setup.sh
# =============================================================================
set -euo pipefail

echo "============================================"
echo "  Overture Pipeline — EC2 Setup"
echo "============================================"

# --------------------------------------------------------------------------
# 1. System packages (auto-detect package manager)
# --------------------------------------------------------------------------
echo ""
echo "[1/4] Installing system packages..."

if command -v dnf >/dev/null 2>&1; then
    echo "Detected dnf (Amazon Linux 2023 / Fedora / RHEL)"
    sudo dnf update -y
    sudo dnf install -y \
        python3 \
        python3-pip \
        python3-devel \
        gcc \
        gcc-c++ \
        make \
        git \
        tar \
        gzip
elif command -v apt-get >/dev/null 2>&1; then
    echo "Detected apt-get (Ubuntu / Debian)"
    sudo apt-get update -y
    sudo apt-get install -y \
        python3 \
        python3-pip \
        python3-venv \
        python3-dev \
        libgdal-dev \
        gdal-bin \
        libgeos-dev \
        libproj-dev \
        build-essential \
        git
else
    echo "ERROR: Could not detect package manager (dnf or apt-get)"
    exit 1
fi

# --------------------------------------------------------------------------
# 2. Python virtual environment
# --------------------------------------------------------------------------
echo ""
echo "[2/4] Creating Python virtual environment..."
cd "$(dirname "$0")"
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip wheel

# --------------------------------------------------------------------------
# 3. Install Python dependencies
# --------------------------------------------------------------------------
echo ""
echo "[3/4] Installing Python dependencies..."
pip install -r requirements.txt

# --------------------------------------------------------------------------
# 4. Pre-download DuckDB extensions
# --------------------------------------------------------------------------
echo ""
echo "[4/4] Pre-downloading DuckDB extensions..."
python3 -c "
import duckdb
con = duckdb.connect()
con.install_extension('httpfs')
con.load_extension('httpfs')
con.install_extension('spatial')
con.load_extension('spatial')
print('DuckDB extensions: httpfs + spatial OK')
"

# --------------------------------------------------------------------------
# Done
# --------------------------------------------------------------------------
echo ""
echo "============================================"
echo "  Setup complete!"
echo "============================================"
echo ""
echo "Activate the virtualenv:"
echo "  source .venv/bin/activate"
echo ""
echo "Run the pipeline for a city:"
echo "  ./run-pipeline.sh sydney 5750005 --hex-agg"
echo ""
echo "With satellite embeddings (requires GEE auth):"
echo "  earthengine authenticate"
echo "  ./run-pipeline.sh sydney 5750005 --satellite --ee-project datacruiser"
echo ""
echo "Or run steps manually:"
echo "  python download_multi_release.py --city sydney --relation-id 5750005 --hex-agg"
echo "  python upload_to_s3.py --city sydney --release 2026-02-18.0 --h3-resolution 9"
echo ""
