import os
import sqlite3
from typing import List, Optional

from core.models import BluetoothDevice, Target


class TargetRepository:
    def __init__(self, path: str) -> None:
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        self.path = path
        self._init_db()

    def _connect(self):
        con = sqlite3.connect(self.path)
        con.row_factory = sqlite3.Row
        return con

    def _init_db(self) -> None:
        with self._connect() as con:
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS targets (
                    address TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    rssi INTEGER,
                    last_seen TEXT NOT NULL
                )
                """
            )

    def upsert(self, device: BluetoothDevice, timestamp: str) -> None:
        with self._connect() as con:
            con.execute(
                """
                INSERT INTO targets(address, name, rssi, last_seen)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(address) DO UPDATE SET
                    name=excluded.name,
                    rssi=excluded.rssi,
                    last_seen=excluded.last_seen
                """,
                (device.address, device.name, device.rssi, timestamp),
            )

    def recent(self, limit: int = 20) -> List[Target]:
        with self._connect() as con:
            rows = con.execute(
                "SELECT address, name, rssi, last_seen FROM targets ORDER BY last_seen DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [Target(**dict(row)) for row in rows]

    def get(self, address: str) -> Optional[Target]:
        with self._connect() as con:
            row = con.execute(
                "SELECT address, name, rssi, last_seen FROM targets WHERE address = ?",
                (address,),
            ).fetchone()
        return Target(**dict(row)) if row else None
