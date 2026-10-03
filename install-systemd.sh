#!/bin/sh
set -eu

PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
RUN_USER=${SUDO_USER:-$(id -un)}
RUN_HOME=$(getent passwd "$RUN_USER" | cut -d: -f6)
BT_INTERFACE=$(awk -F= '/^[[:space:]]*BT_INTERFACE[[:space:]]*=/{gsub(/[[:space:]]/,"",$2); print $2; exit}' "$PROJECT_DIR/.env" 2>/dev/null || true)
BT_INTERFACE=${BT_INTERFACE:-hci0}

if [ ! -f "$PROJECT_DIR/app.py" ]; then
  echo "ERROR: app.py no está en $PROJECT_DIR" >&2
  exit 1
fi

if [ ! -f "$PROJECT_DIR/.env" ]; then
  echo "ERROR: falta $PROJECT_DIR/.env" >&2
  echo "Crea y configura .env antes de instalar el servicio." >&2
  exit 1
fi

RFKILL_BIN=$(command -v rfkill || true)
HCI_BIN=$(command -v hciconfig || true)
BTCTL_BIN=$(command -v bluetoothctl || true)
PYTHON_BIN=$(command -v python3 || true)

for bin in RFKILL_BIN HCI_BIN BTCTL_BIN PYTHON_BIN; do
  eval "path=\${$bin}"
  if [ -z "$path" ]; then
    echo "ERROR: no se encontró el comando requerido: $bin" >&2
    exit 1
  fi
done

# Root service: unblocks rfkill and brings the configured HCI interface up.
sudo tee /etc/systemd/system/bt-telegram-lab-bluetooth.service >/dev/null <<EOF
[Unit]
Description=BT Telegram Lab - Bluetooth bootstrap
After=bluetooth.service
Wants=bluetooth.service
Before=bt-telegram-lab.service

[Service]
Type=oneshot
ExecStart=/bin/sh -c '${RFKILL_BIN} unblock bluetooth || true; i=0; while [ \"\$i\" -lt 15 ]; do ${HCI_BIN} ${BT_INTERFACE} up && exit 0; i=\$((i + 1)); sleep 2; done; exit 1'
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

# User service: runs the Telegram bot without root privileges.
sudo tee /etc/systemd/system/bt-telegram-lab.service >/dev/null <<EOF
[Unit]
Description=BT Telegram Lab Bot
After=network-online.target bluetooth.service bt-telegram-lab-bluetooth.service
Requires=bt-telegram-lab-bluetooth.service
Wants=network-online.target

[Service]
Type=simple
User=${RUN_USER}
Group=${RUN_USER}
WorkingDirectory=${PROJECT_DIR}
ExecStart=${PYTHON_BIN} ${PROJECT_DIR}/app.py
Restart=on-failure
RestartSec=5
TimeoutStopSec=20
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable bt-telegram-lab-bluetooth.service bt-telegram-lab.service
sudo systemctl restart bt-telegram-lab-bluetooth.service
sudo systemctl restart bt-telegram-lab.service

echo
echo "=== Instalación completada ==="
echo "Usuario:       $RUN_USER"
echo "Proyecto:      $PROJECT_DIR"
echo "Interfaz BT:   $BT_INTERFACE"
echo
echo "Comprobar Bluetooth:"
echo "  systemctl status bt-telegram-lab-bluetooth --no-pager"
echo "  bluetoothctl show"
echo "  hciconfig -a"
echo
echo "Comprobar bot:"
echo "  systemctl status bt-telegram-lab --no-pager"
echo "  journalctl -u bt-telegram-lab -f"
