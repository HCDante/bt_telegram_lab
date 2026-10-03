#!/bin/sh
set -eu

sudo apt-get update
sudo apt-get install -y bluez python3

if command -v bluetoothctl >/dev/null 2>&1; then
  echo "bluetoothctl: OK"
else
  echo "ERROR: bluetoothctl not found"
  exit 1
fi

sudo systemctl enable --now bluetooth || true

echo "Install base complete. Configure .env and install systemd service from README.md."
