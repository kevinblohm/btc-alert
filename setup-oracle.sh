#!/usr/bin/env bash
# -------------------------------------------------------------------
# Oracle Cloud VPS setup script
# Run on a fresh Ubuntu instance (Oracle free-tier ARM or AMD)
#
# Usage:  ssh ubuntu@<your-vps-ip> 'bash -s' < setup-oracle.sh
# -------------------------------------------------------------------
set -euo pipefail

APP_DIR="$HOME/btc-alert"

echo "==> Updating packages"
sudo apt-get update -y && sudo apt-get upgrade -y

echo "==> Installing Python 3 + pip"
sudo apt-get install -y python3 python3-pip python3-venv

echo "==> Creating app directory"
mkdir -p "$APP_DIR"

echo "==> Setting up venv"
python3 -m venv "$APP_DIR/venv"
source "$APP_DIR/venv/bin/activate"

echo "==> Installing Python deps"
pip install --upgrade pip
pip install requests twilio python-dotenv

echo "==> Creating systemd service"
sudo tee /etc/systemd/system/btc-alert.service > /dev/null <<EOF
[Unit]
Description=BTC Price Drop Alert Monitor
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/venv/bin/python -u $APP_DIR/monitor.py
Restart=always
RestartSec=30
EnvironmentFile=$APP_DIR/.env

[Install]
WantedBy=multi-user.target
EOF

echo "==> Enabling service"
sudo systemctl daemon-reload
sudo systemctl enable btc-alert.service

echo ""
echo "============================================"
echo "  Setup complete!"
echo ""
echo "  Next steps:"
echo "    1. Copy monitor.py to $APP_DIR/"
echo "    2. Copy .env to $APP_DIR/.env  (fill in your real values)"
echo "    3. Start:   sudo systemctl start btc-alert"
echo "    4. Logs:    journalctl -u btc-alert -f"
echo "============================================"
