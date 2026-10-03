from dataclasses import dataclass, field
from typing import Dict, Optional

from core.models import BluetoothDevice


@dataclass
class ChatSession:
    last_scan: Dict[str, BluetoothDevice] = field(default_factory=dict)
    selected: Optional[BluetoothDevice] = None


class SessionState:
    def __init__(self) -> None:
        self._sessions: Dict[int, ChatSession] = {}

    def get(self, chat_id: int) -> ChatSession:
        return self._sessions.setdefault(chat_id, ChatSession())

    def clear(self, chat_id: int) -> None:
        self._sessions.pop(chat_id, None)
