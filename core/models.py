from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class BluetoothDevice:
    address: str
    name: str
    rssi: Optional[int] = None
    source: str = "unknown"


@dataclass(frozen=True)
class Target:
    address: str
    name: str
    rssi: Optional[int] = None
    last_seen: Optional[str] = None
