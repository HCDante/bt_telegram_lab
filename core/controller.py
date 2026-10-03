import logging
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from bluetooth.info import BluetoothInfo
from bluetooth.scanner import BluetoothScanner
from config import Config
from core.models import BluetoothDevice, Target
from core.state import SessionState
from storage.repository import TargetRepository
from core.action_executor import ActionExecutor

LOG = logging.getLogger(__name__)


class Controller:
    def __init__(self, cfg: Config):
        self.scanner = BluetoothScanner(cfg.bt_scan_seconds, cfg.bt_interface)
        self.repo = TargetRepository(cfg.database_path)
        self.sessions = SessionState()
        self.executor = ActionExecutor(
            interface=cfg.bt_interface,
            packet_size=cfg.bt_disrupt_packet_size,
            delay=cfg.bt_disrupt_delay,
            threads=cfg.bt_disrupt_threads,
        )

    def scan(self, chat_id: int) -> List[BluetoothDevice]:
        devices = self.scanner.scan()
        session = self.sessions.get(chat_id)
        session.last_scan = {d.address.upper(): d for d in devices}
        timestamp = datetime.now(timezone.utc).isoformat()
        for device in devices:
            self.repo.upsert(device, timestamp)
        LOG.info("chat=%s scan_found=%d", chat_id, len(devices))
        return devices

    def recent(self, limit: int = 10) -> List[Target]:
        return self.repo.recent(limit)

    def select(self, chat_id: int, address: str) -> Optional[BluetoothDevice]:
        address = address.strip().upper()
        device = self.sessions.get(chat_id).last_scan.get(address)
        if device is not None:
            self.sessions.get(chat_id).selected = device
        return device

    def select_recent(
        self, chat_id: int, address: str
    ) -> Tuple[Optional[BluetoothDevice], Optional[Target]]:
        """Rediscover a saved target before selecting it.

        The saved target is only selected as an active target when its MAC is
        found during a fresh scan. This prevents stale entries from becoming
        actionable merely because they exist in SQLite.
        """
        address = address.strip().upper()
        saved = self.repo.get(address)
        if saved is None:
            return None, None

        devices = self.scan(chat_id)
        for device in devices:
            if device.address.upper() == address:
                self.sessions.get(chat_id).selected = device
                return device, saved

        self.sessions.get(chat_id).selected = None
        return None, saved

    def selected(self, chat_id: int) -> Optional[BluetoothDevice]:
        return self.sessions.get(chat_id).selected

    def info(self, chat_id: int, address: str):
        target = self.sessions.get(chat_id).selected
        return BluetoothInfo.get(address, self.scanner.scan_seconds, fallback=target)

    def cancel(self, chat_id: int) -> None:
        session = self.sessions.get(chat_id)
        session.selected = None

    # Inicia la acción disruptiva sobre el objetivo seleccionado
    def disrupt(self, chat_id: int, method: str, on_finish=None) -> bool:
        target = self.selected(chat_id)
        if target is None:
            return False
        self.executor.start(chat_id, target.address, method, on_finish=on_finish)
        return True

    def stop_disrupt(self, chat_id: int) -> bool:
        return self.executor.stop(chat_id)
