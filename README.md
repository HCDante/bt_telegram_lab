# 📲📡🦷💥 ToothAche


 _____         _   _     _           _         _          
|_   _|__   ___ | |_| |__ / \   ___| |__   ___| |__   ___ 
  | |/ _ \ / _ \| __| '_ \ _ \ / __| '_ \ / __| '_ \ / _ \
  | | (_) | (_) | |_| | | | / ___ \ (__| | | | (__| | | |  __/
  |_|\___/ \___/ \__|_| |_/_/   \_\___|_| |_|\___|_| |_|\___|

          .---.
         /  🦷  \     [+] Iniciando ToothAche...
        |        |    [+] Buscando adaptador (hci0)...
        |   ^    |    [!] Caries Digital cargada.
         \ \_/ /
          V   V

> ⚠️ **AVISO LEGAL E IMPORTANTE:** Interrumpir comunicaciones ajenas es ilegal en muchos países. Este proyecto está diseñado con fines estrictamente educativos y de investigación. Debe usarse **SOLO** con hardware propio y en entornos controlados de laboratorio. 

Proyecto educativo para **Raspberry Pi 1 Model B**. Permite el control remoto mediante un bot de Telegram para realizar escaneo de redes Bluetooth bajo demanda, selección explícita de objetivos y la ejecución de acciones disruptivas (denegación de servicio, interferencia).

---

## 🎯 Objetivo

El flujo principal de la aplicación es el siguiente:

1. 📱 **Telegram** `/start`
2. 🔍 Comando `/scan`
3. 📡 Escaneo Bluetooth en la Raspberry
4. 📋 Despliegue de lista de dispositivos encontrados
5. 🎯 Selección de un objetivo
6. ✅ Confirmación
7. ⚡ **Acción disruptiva**

Esta versión **no** usa micrófono ni algoritmos de Machine Learning. Implementa rutinas de interferencia, *flood*, desconexión forzada o generación masiva de tráfico Bluetooth. El `ActionExecutor` está completamente operativo y expone dos métodos disruptivos seleccionables desde Telegram.

---

## 🛠️ Hardware Necesario

- **Raspberry Pi 1 Model B** (Arquitectura ARM1176/ARMv6).
- **Sistema Operativo:** Raspberry Pi OS 32-bit (se recomienda la versión *Legacy* para mayor estabilidad en la Pi 1).
- **Conectividad:** Ethernet o adaptador de red USB.
- **Bluetooth:** Dongle Bluetooth USB compatible con Linux/BlueZ (Obligatorio, ya que la Pi 1 no incorpora BT nativo).
- **Almacenamiento:** Tarjeta microSD.

---

## 📦 Dependencias

El proyecto está pensado para funcionar **sin instalar paquetes de Python de terceros**, utilizando únicamente la biblioteca estándar (para HTTPS vía `urllib` y `json`). 

A nivel de sistema requiere:
- `python3`
- `bluetoothctl` (BlueZ) o, como fallback, `hcitool`.
- `rfcomm` (paquete `bluez` / `bluez-tools`).
- `l2ping` (paquete `bluez`).
- `systemd` (opcional, para ejecución automática como servicio).

---

## 🚀 Instalación y Configuración

### 1. Crear y configurar el bot

En Telegram, inicia una conversación con [@BotFather](https://t.me/botfather), crea un nuevo bot y copia el **Token** proporcionado.

Clona el repositorio y configura las variables de entorno:

```bash
cp .env.example .env
nano .env
```

Edita el archivo `.env` con tus datos:

```ini
TELEGRAM_BOT_TOKEN=123456:ABC...
AUTHORIZED_CHAT_IDS=123456789
BT_SCAN_SECONDS=8

# --- Variables opcionales para acciones disruptivas ---
BT_INTERFACE=hci0
BT_DISRUPT_PACKET_SIZE=800  # Tamaño de paquete para l2ping (bytes)
BT_DISRUPT_DELAY=0.5        # Pausa entre reintentos (segundos)
BT_DISRUPT_THREADS=4        # Repeticiones por ciclo en el método rfcomm
```
*(Nota: `AUTHORIZED_CHAT_IDS` admite varios IDs separados por comas).*

### 2. Preparar el adaptador Bluetooth

Comprueba que el sistema detecta tu dongle Bluetooth (normalmente `hci0`):

```bash
hciconfig -a
bluetoothctl show
```

Realiza una prueba de escaneo manual para verificar que BlueZ funciona correctamente:

```bash
bluetoothctl
# Dentro de la consola de bluetoothctl ejecuta:
power on
scan on
# Espera unos segundos y luego:
scan off
exit
```

### 3. Ejecutar manualmente

Para probar el bot de forma interactiva:

```bash
cd ~/bt-telegram-lab
python3 app.py
```

Ve a tu bot en Telegram y envía el comando `/start`.

---

## ⚙️ Instalación como Servicio (Systemd)

Si deseas que el bot arranque automáticamente al encender la Raspberry Pi:

1. **Copiar archivos a `/opt`:**
   ```bash
   sudo mkdir -p /opt/bt-telegram-lab
   sudo cp -r . /opt/bt-telegram-lab/
   sudo chown -R pi:pi /opt/bt-telegram-lab
   ```

2. **Copiar y ajustar el entorno:**
   ```bash
   sudo cp /opt/bt-telegram-lab/.env.example /opt/bt-telegram-lab/.env
   sudo nano /opt/bt-telegram-lab/.env
   ```

3. **Habilitar e iniciar el servicio:**
   ```bash
   sudo cp systemd/bt-telegram-lab.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now bt-telegram-lab
   ```

4. **Ver los logs en tiempo real:**
   ```bash
   journalctl -u bt-telegram-lab -f
   ```

---

## 🕹️ Comandos de Telegram

- `/start` - Despliega el menú principal.
- `/scan` - Inicia un escaneo Bluetooth manual.
- `/status` - Muestra el estado del servicio y el último objetivo seleccionado.
- `/cancel` - Cancela la selección del objetivo actual.

### Interfaz del Objetivo
Tras seleccionar un dispositivo, el bot te ofrecerá las siguientes opciones mediante botones:
* ℹ️ **Ver información:** Consulta información de BlueZ sin interactuar con el dispositivo.
* 🦷 **Caries Digital:** Abre el submenú de *acciones disruptivas*.
* ❌ **Cancelar:** Libera el objetivo actual.

---

## ⚡ Acciones Disruptivas

Desde el submenú **Caries Digital**, tienes acceso a dos métodos de prueba de estrés:

1. **RFCOMM Connect:** 
   Ejecuta `rfcomm connect <MAC> 1` de forma cíclica. Puede forzar la desconexión de dispositivos (ej. altavoces) que solo admiten una conexión activa a la vez.
2. **L2CAP Flood:** 
   Ejecuta `l2ping -i <iface> -s <size> -f <MAC>`. Satura el enlace Bluetooth del objetivo enviando ráfagas continuas de paquetes L2CAP de gran tamaño.

> **Nota técnica:** La acción se ejecuta en un hilo independiente (Thread) por chat. Esto asegura que el bot de Telegram siga respondiendo. El usuario puede detener el ataque en cualquier momento con el botón **Detener** y recibirá una notificación al finalizar.

---

## 🏗️ Arquitectura del Software

```text
app.py
 ├── TelegramBot
 │    └── Telegram API vía HTTPS (urllib)
 │
 └── Controller
      ├── BluetoothScanner
      ├── TargetRepository (SQLite)
      ├── SessionState
      └── ActionExecutor
           ├── rfcomm
           └── l2ping
```

---

## 🍓 Compatibilidad con Raspberry Pi 1

* **Dependencias Ligeras:** Evita añadir dependencias de Python (como `pip install ...`) que requieran compilar ruedas binarias modernas. Si necesitas una librería externa en el futuro, verifica su compatibilidad con `ARMv6/32-bit` o compílala directamente en la placa.
* **Uso de CPU:** Modera los valores de `BT_DISRUPT_THREADS` y `BT_DISRUPT_PACKET_SIZE`. La Pi 1 tiene recursos muy limitados y valores demasiado agresivos pueden saturar la CPU al 100%, degradando el propio enlace Bluetooth del dongle o bloqueando el sistema.

---

## 🗺️ Próxima etapa (Roadmap)

La siguiente iteración del proyecto tiene previsto abordar:

- [ ] 1. Mejor identificación de dispositivos y lectura de intensidad de señal (RSSI).
- [ ] 2. Registro histórico de objetivos escaneados.
- [ ] 3. Expiración de objetivos cacheados en escaneos anteriores.
- [ ] 4. Pruebas unitarias/automatizadas del parser de resultados Bluetooth.
- [ ] 5. Arquitectura basada en *plugins* para añadir fácilmente nuevas acciones de laboratorio.