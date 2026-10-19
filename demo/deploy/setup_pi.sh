#!/usr/bin/env bash
# Install the AI ordering demo on a Raspberry Pi 5 (Raspberry Pi OS 64-bit, Bookworm or later)
# and publish it to your tailnet over HTTPS with `tailscale serve`.
#
# Run from the demo folder on the Pi:   bash deploy/setup_pi.sh
set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SERVICE=ai-ordering-demo
PORT="${PORT:-10050}"          # the app, bound to 127.0.0.1 only
SERVE_PORT="${SERVE_PORT:-10051}"  # HTTPS port tailscale serve exposes on the tailnet

echo "==> App folder: $APP_DIR"

if [ "$(uname -m)" != "aarch64" ]; then
  echo "!! This needs a 64-bit OS (aarch64). Found: $(uname -m)" >&2
  exit 1
fi

echo "==> System packages"
sudo apt-get update
sudo apt-get install -y python3-venv python3-dev build-essential libssl-dev ca-certificates libasound2 libopus0 libvpx-dev

PY=python3
"$PY" -c 'import sys; assert sys.version_info >= (3, 11), "Python 3.11+ is required"'

echo "==> Python virtualenv + dependencies (takes a few minutes on first run)"
"$PY" -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/pip" install --upgrade pip
"$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt"

if [ ! -f "$APP_DIR/.env" ]; then
  cp "$APP_DIR/.env.example" "$APP_DIR/.env"
  echo "!! Created $APP_DIR/.env from the template: fill in your API keys, then rerun this script."
  exit 1
fi

echo "==> systemd service"
sudo tee /etc/systemd/system/$SERVICE.service >/dev/null <<EOF
[Unit]
Description=Restaurant Quimper AI ordering demo
After=network-online.target tailscaled.service
Wants=network-online.target

[Service]
User=$USER
WorkingDirectory=$APP_DIR
Environment=HOST=127.0.0.1
Environment=PORT=$PORT
ExecStart=$APP_DIR/.venv/bin/python $APP_DIR/server.py
Restart=on-failure
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable --now $SERVICE
sleep 3
curl -fsS "http://127.0.0.1:$PORT/api/config" && echo

echo "==> Publish on the tailnet over HTTPS"
sudo tailscale serve --bg --https="$SERVE_PORT" "http://127.0.0.1:$PORT"
tailscale serve status

DNS_NAME="$(tailscale status --json | "$APP_DIR/.venv/bin/python" -c 'import json,sys; print(json.load(sys.stdin)["Self"]["DNSName"].rstrip("."))')"
echo
echo "Done. On a phone signed in to your tailnet open:  https://$DNS_NAME:$SERVE_PORT"
echo "Kitchen board:                                     https://$DNS_NAME:$SERVE_PORT/kitchen"
echo "Logs:   journalctl -u $SERVICE -f"
