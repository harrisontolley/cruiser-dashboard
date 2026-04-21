#!/usr/bin/env bash
# =============================================================================
# EC2 setup for the traffic-incident scraper.
#
# Target: Amazon Linux 2023 (dnf) or Ubuntu 22.04/24.04 (apt) — auto-detected.
# Recommended instance: t4g.nano (2 vCPU, 0.5 GB). Scraper is I/O-bound, tiny.
# Storage: 10 GB gp3 is ample.
# IAM: attach the role described in deploy/iam-policy.json (S3 write on
#      the traffic-incidents prefix only).
#
# This script:
#   1. Installs OS packages
#   2. Creates /opt/traffic-scraper with a Python venv
#   3. Copies poll.py + backfill_tfnsw.py + test_sources.py + .env.example
#   4. Installs the systemd unit + timer
#   5. Enables the timer (but does NOT start polling — you'll fill in .env first)
#
# Usage (run as a user with sudo access, from the scraper/ directory):
#   chmod +x deploy/ec2-setup.sh
#   sudo deploy/ec2-setup.sh
# =============================================================================
set -euo pipefail

INSTALL_DIR=/opt/traffic-scraper
SERVICE_USER="${SUDO_USER:-ubuntu}"

echo "============================================"
echo "  Traffic scraper — EC2 setup"
echo "  Install dir: $INSTALL_DIR"
echo "  Run as user: $SERVICE_USER"
echo "============================================"

# -----------------------------------------------------------------------------
# 1. OS packages
# -----------------------------------------------------------------------------
echo "[1/5] Installing system packages..."
if command -v dnf >/dev/null 2>&1; then
    sudo dnf -y update
    sudo dnf -y install python3 python3-pip python3-devel gcc make tar gzip
elif command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update -y
    sudo apt-get install -y python3 python3-venv python3-pip python3-dev build-essential
else
    echo "ERROR: neither dnf nor apt-get found"
    exit 1
fi

# -----------------------------------------------------------------------------
# 2. Copy code to /opt/traffic-scraper
# -----------------------------------------------------------------------------
echo "[2/5] Copying scraper code to $INSTALL_DIR..."
SCRAPER_SRC="$(cd "$(dirname "$0")/.." && pwd)"

sudo mkdir -p "$INSTALL_DIR"
sudo cp "$SCRAPER_SRC/poll.py" "$INSTALL_DIR/"
sudo cp "$SCRAPER_SRC/backfill_tfnsw.py" "$INSTALL_DIR/"
sudo cp "$SCRAPER_SRC/test_sources.py" "$INSTALL_DIR/"
sudo cp "$SCRAPER_SRC/requirements.txt" "$INSTALL_DIR/"
# Only seed .env if one doesn't already exist — preserves any keys you've set
if [ ! -f "$INSTALL_DIR/.env" ]; then
    sudo cp "$SCRAPER_SRC/.env.example" "$INSTALL_DIR/.env"
    sudo chmod 600 "$INSTALL_DIR/.env"
fi
sudo chown -R "$SERVICE_USER":"$SERVICE_USER" "$INSTALL_DIR"

# -----------------------------------------------------------------------------
# 3. Python venv + deps
# -----------------------------------------------------------------------------
echo "[3/5] Creating venv + installing Python deps..."
sudo -u "$SERVICE_USER" python3 -m venv "$INSTALL_DIR/.venv"
sudo -u "$SERVICE_USER" "$INSTALL_DIR/.venv/bin/pip" install --upgrade pip wheel
sudo -u "$SERVICE_USER" "$INSTALL_DIR/.venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt"

# -----------------------------------------------------------------------------
# 4. systemd unit + timer
# -----------------------------------------------------------------------------
echo "[4/5] Installing systemd unit + timer..."
# If the service user differs from the default (ubuntu), rewrite the unit
if [ "$SERVICE_USER" != "ubuntu" ]; then
    sudo sed -e "s/^User=ubuntu/User=$SERVICE_USER/" \
             -e "s/^Group=ubuntu/Group=$SERVICE_USER/" \
             "$SCRAPER_SRC/deploy/traffic-scraper.service" \
             | sudo tee /etc/systemd/system/traffic-scraper.service >/dev/null
else
    sudo cp "$SCRAPER_SRC/deploy/traffic-scraper.service" /etc/systemd/system/
fi
sudo cp "$SCRAPER_SRC/deploy/traffic-scraper.timer" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable traffic-scraper.timer

# -----------------------------------------------------------------------------
# 5. Next-steps banner
# -----------------------------------------------------------------------------
echo ""
echo "============================================"
echo "  Setup complete!"
echo "============================================"
echo ""
echo "Next steps:"
echo "  1. Fill in API keys:"
echo "       sudoedit $INSTALL_DIR/.env"
echo ""
echo "  2. Smoke-test (no S3 writes):"
echo "       sudo -u $SERVICE_USER bash -c 'cd $INSTALL_DIR && set -a && source .env && set +a && .venv/bin/python test_sources.py'"
echo ""
echo "  3. One-shot production run (writes to S3):"
echo "       sudo systemctl start traffic-scraper.service"
echo "       journalctl -u traffic-scraper.service -n 50"
echo ""
echo "  4. Start the 5-minute timer:"
echo "       sudo systemctl start traffic-scraper.timer"
echo "       systemctl list-timers | grep traffic-scraper"
echo ""
echo "  5. Tail logs:"
echo "       journalctl -u traffic-scraper.service -f"
