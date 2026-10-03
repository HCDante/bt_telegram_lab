import logging
from datetime import datetime, timezone

from core.models import BluetoothDevice

LOG = logging.getLogger(__name__)


class ActionExecutor:
    """Laboratory-safe action layer.

    This MVP deliberately does not implement interference, flooding,
    forced-disconnect or packet-generation routines.
    """

    def simulate(self, target: BluetoothDevice) -> str:
        timestamp = datetime.now(timezone.utc).isoformat()
        LOG.warning("SIMULATION target=%s name=%s time=%s", target.address, target.name, timestamp)
        return (
            "Acción simulada correctamente.\n"
            f"Objetivo: {target.name}\n"
            f"MAC: {target.address}\n"
            f"Hora UTC: {timestamp}"
        )
