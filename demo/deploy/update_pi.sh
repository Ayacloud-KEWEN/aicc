#!/usr/bin/env bash
# Pull the latest code from GitHub and restart the demo on the Raspberry Pi.
# Run from the demo folder:   bash deploy/update_pi.sh
set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SERVICE=ai-ordering-demo

cd "$APP_DIR"
echo "==> git pull"
git pull --ff-only

echo "==> Python dependencies"
"$APP_DIR/.venv/bin/pip" install -q -r "$APP_DIR/requirements.txt"

echo "==> Restart $SERVICE"
sudo systemctl restart "$SERVICE"
sleep 3
systemctl --no-pager --lines=0 status "$SERVICE" | head -3
git log --oneline -1
