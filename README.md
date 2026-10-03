# BT Telegram Lab

MVP educativo para Raspberry Pi 1 Model B: control por Telegram, escaneo Bluetooth bajo demanda, selección explícita de un objetivo y acciones disruptivas.

## Objetivo

Flujo principal:

```text
Telegram /start
   -> /scan
   -> escaneo Bluetooth
   -> lista de dispositivos
   -> selección
   -> confirmación
   -> acción de laboratorio
```

Esta versión **no usa micrófono, Machine Learning ni carga continua**. Tampoco implementa rutinas de interferencia, flood, desconexión forzada ni generación masiva de tráfico Bluetooth. El `ActionExecutor` queda preparado para ampliar el proyecto con experimentos controlados sobre hardware propio.

## Hardware

- Raspberry Pi 1 Model B
- Raspberry Pi OS 32-bit
- Ethernet o adaptador de red USB
- Dongle Bluetooth USB compatible con Linux/BlueZ
- microSD

La Raspberry Pi 1 usa ARM1176/ARMv6 y no incorpora Bluetooth; el dongle es obligatorio para este proyecto. La documentación actual de Raspberry Pi sigue ofreciendo Raspberry Pi OS 32-bit compatible con todos los modelos. Para máxima compatibilidad con una Pi 1 antigua, si el sistema actual presenta problemas con la imagen estándar, conviene usar una imagen Legacy 32-bit disponible para Pi 1. 

## Dependencias

El proyecto está pensado para funcionar sin instalar paquetes de Python de terceros:

- Python 3
- `bluetoothctl` (BlueZ) o, como fallback, `hcitool`
- `systemd` opcional para arrancar automáticamente

La comunicación con Telegram usa HTTPS mediante `urllib` y JSON de la biblioteca estándar.

## 1. Crear el bot

En Telegram, abre `@BotFather`, crea un bot y copia su token.

Crea `.env` a partir de `.env.example`:

```bash
cp .env.example .env
nano .env
```

Configura:

```text
TELEGRAM_BOT_TOKEN=123456:ABC...
AUTHORIZED_CHAT_IDS=123456789
BT_SCAN_SECONDS=8
```

`AUTHORIZED_CHAT_IDS` admite varios IDs separados por coma.

## 2. Preparar Bluetooth

Comprueba el adaptador:

```bash
hciconfig -a
bluetoothctl show
```

Debes tener una interfaz Bluetooth disponible, normalmente `hci0`.

Prueba un escaneo manual:

```bash
bluetoothctl
```

y dentro:

```text
power on
scan on
```

Espera unos segundos y usa:

```text
scan off
exit
```

## 3. Ejecutar manualmente

```bash
cd ~/bt-telegram-lab
python3 app.py
```

Después, en Telegram:

```text
/start
```

## 4. Instalar como servicio

Copia el proyecto a `/opt`:

```bash
sudo mkdir -p /opt/bt-telegram-lab
sudo cp -r . /opt/bt-telegram-lab/
sudo chown -R pi:pi /opt/bt-telegram-lab
```

Copia el entorno:

```bash
sudo cp /opt/bt-telegram-lab/.env.example /opt/bt-telegram-lab/.env
sudo nano /opt/bt-telegram-lab/.env
```

Instala el servicio:

```bash
sudo cp systemd/bt-telegram-lab.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now bt-telegram-lab
```

Ver logs:

```bash
journalctl -u bt-telegram-lab -f
```

## Comandos de prueba

- `/start` menú principal
- `/scan` escaneo manual
- `/status` estado del servicio y último objetivo
- `/cancel` cancela la selección actual

Tras seleccionar un objetivo, la interfaz ofrece:

- `ℹ️ Ver información`: consulta información de BlueZ sin modificar el dispositivo.
- `🧪 Simular acción`: registra la operación como simulación y no transmite tráfico adicional al objetivo.

## Arquitectura

```text
app.py
 ├── TelegramBot
 │     └── Telegram API por HTTPS
 │
 └── Controller
       ├── BluetoothScanner
       ├── TargetRepository (SQLite)
       ├── SessionState
       └── ActionExecutor
```

## Compatibilidad con Pi 1

Evita añadir dependencias que requieran ruedas binarias modernas. Si posteriormente se necesita una librería externa, primero se debe comprobar que exista una versión compatible con ARMv6/32-bit o compilarla localmente.

## Próxima etapa

La siguiente iteración puede añadir:

1. mejor identificación de dispositivos y RSSI;
2. historial de objetivos;
3. expiración de objetivos encontrados en escaneos anteriores;
4. pruebas automatizadas del parser Bluetooth;
5. una capa de plugins para acciones de laboratorio autorizadas.
