import json
import logging
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from config import Config
from core.controller import Controller
from core.models import BluetoothDevice, Target

LOG = logging.getLogger(__name__)


class TelegramBot:
    API_BASE = "https://api.telegram.org/bot{}"

    def __init__(self, cfg: Config, controller: Controller):
        self.cfg = cfg
        self.controller = controller
        self.offset: Optional[int] = None

    def run(self) -> None:
        me = self.api("getMe")
        LOG.info("Telegram bot started: @%s", me.get("username", "unknown"))
        while True:
            try:
                updates = self.api(
                    "getUpdates",
                    {
                        "timeout": 20,
                        "allowed_updates": json.dumps(["message", "callback_query"]),
                        **({"offset": self.offset} if self.offset is not None else {}),
                    },
                    timeout=35,
                )
                for update in updates:
                    self.offset = update["update_id"] + 1
                    self.handle_update(update)
            except KeyboardInterrupt:
                raise
            except Exception:
                LOG.exception("Polling error")
                time.sleep(3)

    def handle_update(self, update: Dict[str, Any]) -> None:
        if "message" in update:
            msg = update["message"]
            chat_id = msg["chat"]["id"]
            if not self.authorized(chat_id):
                self.send_message(chat_id, "No autorizado.")
                return
            text = (msg.get("text") or "").strip()
            if text.startswith("/"):
                self.handle_command(chat_id, text.split()[0].lower())
            return

        if "callback_query" in update:
            cb = update["callback_query"]
            chat_id = cb["message"]["chat"]["id"]
            self.api("answerCallbackQuery", {"callback_query_id": cb["id"]})
            if not self.authorized(chat_id):
                self.send_message(chat_id, "No autorizado.")
                return
            self.handle_callback(chat_id, cb.get("data", ""))

    def authorized(self, chat_id: int) -> bool:
        return chat_id in self.cfg.authorized_chat_ids

    def handle_command(self, chat_id: int, command: str) -> None:
        if command in ("/start", "/menu"):
            self.show_menu(chat_id)
        elif command == "/scan":
            self.do_scan(chat_id)
        elif command == "/status":
            self.do_status(chat_id)
        elif command == "/recent":
            self.send_recent(chat_id)
        elif command == "/cancel":
            self.controller.cancel(chat_id)
            self.send_message(chat_id, "Selección cancelada.")
        else:
            self.send_message(chat_id, "Comando desconocido. Usa /start.")

    def show_menu(self, chat_id: int) -> None:
        keyboard = [
            [{"text": "🔍 Escanear Bluetooth", "callback_data": "scan"}],
            [{"text": "📋 Objetivos recientes", "callback_data": "recent"}],
            [{"text": "📡 Estado", "callback_data": "status"}],
        ]
        self.send_message(chat_id, "BT Telegram Lab\nSelecciona una operación:", keyboard)

    def do_scan(self, chat_id: int) -> None:
        self.send_message(chat_id, "🔍 Escaneando Bluetooth...")
        try:
            devices = self.controller.scan(chat_id)
        except Exception as exc:
            LOG.exception("Scan failed")
            self.send_message(chat_id, f"Error durante el escaneo: {exc}")
            return

        if not devices:
            self.send_message(chat_id, "No se encontraron dispositivos.")
            return

        buttons = []
        for device in devices[:12]:
            label = self._device_label(device)
            buttons.append([{"text": label, "callback_data": f"select:{device.address}"}])
        buttons.append([{"text": "🔄 Repetir escaneo", "callback_data": "scan"}])
        self.send_message(chat_id, f"Encontrados: {len(devices)}\nSelecciona un objetivo:", buttons)

    def do_status(self, chat_id: int) -> None:
        target = self.controller.selected(chat_id)
        if target:
            text = f"Objetivo seleccionado:\n{target.name}\n{target.address}"
        else:
            text = "Sin objetivo seleccionado."
        self.send_message(chat_id, text)

    def handle_callback(self, chat_id: int, data: str) -> None:
        if data == "scan":
            self.do_scan(chat_id)
            return
        if data == "status":
            self.do_status(chat_id)
            return
        if data == "recent":
            self.send_recent(chat_id)
            return
        if data.startswith("select:"):
            address = data.split(":", 1)[1]
            target = self.controller.select(chat_id, address)
            if not target:
                self.send_message(chat_id, "Ese objetivo ya no está en el último escaneo. Ejecuta /scan nuevamente.")
                return
            self.show_target(chat_id, target)
            return
        if data.startswith("recent_select:"):
            address = data.split(":", 1)[1]
            self.verify_recent_target(chat_id, address)
            return
        if data == "info":
            target = self.controller.selected(chat_id)
            if not target:
                self.send_message(chat_id, "No hay un objetivo seleccionado.")
                return
            try:
                info = self.controller.info(chat_id, target.address)
            except Exception as exc:
                LOG.exception("BlueZ info failed")
                self.send_message(chat_id, f"Error obteniendo información BlueZ: {exc}")
                return
            lines = [f"{k}: {v}" for k, v in info.items()]
            self.send_message(chat_id, "ℹ️ Información BlueZ\n\n" + "\n".join(lines))
            return
        if data == "cancel":
            self.controller.cancel(chat_id)
            self.send_message(chat_id, "Selección cancelada.")
            return

        #Manejar los callbacks de la acción  
        if data == "disrupt_menu":
            self.show_disrupt_menu(chat_id)
            return
        if data.startswith("disrupt:"):
            method = data.split(":", 1)[1]
            self.start_disrupt(chat_id, method)
            return
        if data == "disrupt_stop":
            self.stop_disrupt(chat_id)
            return
        if data == "back_to_target":
            target = self.controller.selected(chat_id)
            if target:
                self.show_target(chat_id, target)
            else:
                self.send_message(chat_id, "No hay objetivo seleccionado.")
            return

    def show_target(self, chat_id: int, target: BluetoothDevice, verified: bool = False) -> None:
        keyboard = [
            [{"text": "ℹ️ Ver información", "callback_data": "info"}],
            [{"text": "🦷 Caries Digital", "callback_data": "disrupt_menu"}],
            [{"text": "❌ Cancelar", "callback_data": "cancel"}],
        ]
        verification = "\nEstado: ✅ encontrado en el último escaneo." if verified else ""
        self.send_message(
            chat_id,
            f"Objetivo seleccionado:\n\nNombre: {target.name}\nMAC: {target.address}{verification}\n\nSelecciona una operación para este objetivo.",
            keyboard,
        )

    def send_recent(self, chat_id: int) -> None:
        recent = self.controller.recent(10)
        if not recent:
            self.send_message(chat_id, "Todavía no hay objetivos guardados.")
            return

        lines = []
        buttons = []
        for item in recent:
            lines.append(
                f"• {item.name} — {item.address}\n  Último escaneo: {self._format_seen(item.last_seen)}"
            )
            buttons.append([
                {
                    "text": f"🎯 {self._short_name(item.name)}",
                    "callback_data": f"recent_select:{item.address}",
                }
            ])
        buttons.append([{"text": "🔍 Nuevo escaneo", "callback_data": "scan"}])
        self.send_message(chat_id, "📋 Objetivos recientes\n\n" + "\n".join(lines) + "\n\nSelecciona uno para verificarlo nuevamente.", buttons)

    def verify_recent_target(self, chat_id: int, address: str) -> None:
        address = address.strip().upper()
        self.send_message(chat_id, "🔄 Verificando objetivo mediante un nuevo escaneo...")
        try:
            target, saved = self.controller.select_recent(chat_id, address)
        except Exception as exc:
            LOG.exception("Recent target verification failed")
            self.send_message(chat_id, f"Error verificando el objetivo: {exc}")
            return

        if target is None:
            if saved is None:
                self.send_message(chat_id, "Ese objetivo ya no existe en la base local.")
                return
            self.send_message(
                chat_id,
                "⚪ Objetivo no detectado en el escaneo actual.\n\n"
                f"Nombre: {saved.name}\n"
                f"MAC: {saved.address}\n"
                f"Último registro: {self._format_seen(saved.last_seen)}\n\n"
                "No se ha seleccionado para ninguna operación.",
            )
            return

        self.show_target(chat_id, target, verified=True)

    @staticmethod
    def _device_label(device: BluetoothDevice) -> str:
        return f"{TelegramBot._short_name(device.name)} · {device.address}"

    @staticmethod
    def _short_name(name: str, limit: int = 24) -> str:
        clean = (name or "Unknown").strip() or "Unknown"
        return clean if len(clean) <= limit else clean[: limit - 1] + "…"

    @staticmethod
    def _format_seen(value: Optional[str]) -> str:
        if not value:
            return "desconocido"
        try:
            stamp = datetime.fromisoformat(value)
            if stamp.tzinfo is None:
                stamp = stamp.replace(tzinfo=timezone.utc)
            delta = datetime.now(timezone.utc) - stamp.astimezone(timezone.utc)
            seconds = max(0, int(delta.total_seconds()))
            if seconds < 60:
                return "hace menos de 1 min"
            minutes = seconds // 60
            if minutes < 60:
                return f"hace {minutes} min"
            hours = minutes // 60
            if hours < 24:
                return f"hace {hours} h"
            return f"hace {hours // 24} d"
        except ValueError:
            return value

    def send_message(self, chat_id: int, text: str, keyboard=None) -> None:
        payload = {"chat_id": chat_id, "text": text}
        if keyboard:
            payload["reply_markup"] = json.dumps({"inline_keyboard": keyboard})
        self.api("sendMessage", payload)

    def api(self, method: str, params: Optional[Dict[str, Any]] = None, timeout: int = 15):
        url = self.API_BASE.format(self.cfg.telegram_bot_token) + "/" + method
        data = urllib.parse.urlencode(params or {}).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
        if not body.get("ok"):
            raise RuntimeError(body.get("description", "Telegram API error"))
        return body.get("result")
    
    #Meétodos auxiliares para interferencia
    def show_disrupt_menu(self, chat_id: int) -> None:
        keyboard = [
            [{"text": "📡 RFCOMM Connect", "callback_data": "disrupt:rfcomm"}],
            [{"text": "🌊 L2CAP Flood", "callback_data": "disrupt:l2ping"}],
            [{"text": "⬅️ Volver", "callback_data": "back_to_target"}],
        ]
        self.send_message(
            chat_id,
            "Selecciona el método de interrupción:",
            keyboard,
        )

    def start_disrupt(self, chat_id: int, method: str) -> None:
        target = self.controller.selected(chat_id)
        if not target:
            self.send_message(chat_id, "No hay objetivo seleccionado.")
            return

        def on_finish(cid: int, m: str) -> None:
            try:
                self.send_message(cid, f"✅ Acción {m} finalizada.")
            except Exception:
                LOG.exception("No se pudo notificar el fin de la acción")

        try:
            self.controller.disrupt(chat_id, method, on_finish=on_finish)
        except RuntimeError:
            self.send_message(chat_id, "⚠️ Ya hay una acción en curso. Pulsa Detener primero.")
            return
        except Exception as exc:
            self.send_message(chat_id, f"Error al iniciar: {exc}")
            return

        keyboard = [[{"text": "⏹ Detener", "callback_data": "disrupt_stop"}]]
        self.send_message(
            chat_id,
            f"🦷 Caries Digital activada ({method}) sobre {target.name}\n"
            f"MAC: {target.address}\nPulsa Detener para finalizar.",
            keyboard,
        )

    def stop_disrupt(self, chat_id: int) -> None:
        if self.controller.stop_disrupt(chat_id):
            self.send_message(chat_id, "⏹ Acción detenida.")
        else:
            self.send_message(chat_id, "No hay acción en curso.")
