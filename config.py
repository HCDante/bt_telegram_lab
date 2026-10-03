import os
from dataclasses import dataclass


def _load_dotenv(path: str = ".env") -> None:
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)


@dataclass(frozen=True)
class Config:
    telegram_bot_token: str
    authorized_chat_ids: frozenset[int]
    bt_scan_seconds: int
    bt_interface: str
    log_level: str
    database_path: str


def load_config() -> Config:
    _load_dotenv()
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured")

    raw_ids = os.environ.get("AUTHORIZED_CHAT_IDS", "")
    ids = set()
    for item in raw_ids.split(","):
        item = item.strip()
        if item:
            ids.add(int(item))
    if not ids:
        raise RuntimeError("AUTHORIZED_CHAT_IDS is not configured")

    return Config(
        telegram_bot_token=token,
        authorized_chat_ids=frozenset(ids),
        bt_scan_seconds=max(3, int(os.environ.get("BT_SCAN_SECONDS", "8"))),
        bt_interface=os.environ.get("BT_INTERFACE", "hci0"),
        log_level=os.environ.get("LOG_LEVEL", "INFO"),
        database_path=os.environ.get("DATABASE_PATH", "data/targets.db"),
    )
