import logging
import re
import shutil
import subprocess
from typing import List

from core.models import BluetoothDevice

LOG = logging.getLogger(__name__)
ANSI_ESCAPE_RE = re.compile(r"\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

MAC_RE = r"(?P<mac>(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2})"

# Propiedades de BlueZ que NUNCA deben convertirse en nombres.
PROPERTY_PREFIXES = (
    "name:",
    "alias:",
    "rssi:",
    "txpower:",
    "paired:",
    "bonded:",
    "trusted:",
    "blocked:",
    "connected:",
    "legacypairing:",
    "icon:",
    "class:",
    "modalias:",
    "uuids:",
    "uuid:",
    "manufacturerdata:",
    "servicedata:",
    "servicesresolved:",
)


class BluetoothScanner:
    def __init__(self, scan_seconds: int = 8, interface: str = "hci0"):
        self.scan_seconds = scan_seconds
        self.interface = interface

    def scan(self) -> List[BluetoothDevice]:
        if not shutil.which("bluetoothctl"):
            raise RuntimeError("bluetoothctl is not installed")

        return self._scan_bluetoothctl()

    def _scan_bluetoothctl(self) -> List[BluetoothDevice]:
        # Usamos exactamente la misma secuencia que funciona de forma
        # interactiva en la Raspberry:
        # power on -> scan on -> esperar -> scan off -> quit
        shell_script = (
            "{ "
            "printf 'power on\\n'; "
            "printf 'scan on\\n'; "
            f"sleep {int(self.scan_seconds)}; "
            "printf 'scan off\\n'; "
            "printf 'quit\\n'; "
            "} | bluetoothctl 2>&1"
        )

        proc = subprocess.run(
            ["bash", "-lc", shell_script],
            capture_output=True,
            text=True,
            timeout=self.scan_seconds + 15,
            check=False,
        )

        output = proc.stdout or ""

        if not output.strip():
            raise RuntimeError(
                proc.stderr.strip() or "bluetoothctl produced no output"
            )

        devices = self._parse_bluetoothctl(output.splitlines())

        if not devices:
            raise RuntimeError(
                "bluetoothctl scan completed but no devices were parsed"
            )

        return devices

    @staticmethod
    def _parse_bluetoothctl(lines) -> List[BluetoothDevice]:
        found = {}

        for raw_line in lines:
            line = ANSI_ESCAPE_RE.sub("", raw_line).strip()

            if not line:
                continue

            # Identificar el tipo de evento.
            is_new = line.startswith("[NEW] ")
            is_changed = line.startswith("[CHG] ")
            is_removed = line.startswith("[DEL] ")

            if is_removed:
                continue

            if is_new or is_changed:
                line = line[6:].strip()

            match = re.match(
                rf"^Device\s+{MAC_RE}(?:\s+(?P<rest>.*))?$",
                line,
            )

            if not match:
                continue

            address = match.group("mac").upper()
            rest = (match.group("rest") or "").strip()
            lower_rest = rest.lower()

            existing = found.get(address)

            # ---------------------------------------------------------
            # [CHG] Device MAC Name: ...
            # [CHG] Device MAC Alias: ...
            # ---------------------------------------------------------
            if is_changed:
                if lower_rest.startswith("name:"):
                    name = rest.split(":", 1)[1].strip()

                    if name:
                        rssi = existing.rssi if existing else None
                        found[address] = BluetoothDevice(
                            address,
                            name,
                            rssi=rssi,
                            source="bluetoothctl",
                        )

                elif lower_rest.startswith("alias:"):
                    alias = rest.split(":", 1)[1].strip()

                    if alias and (
                        existing is None
                        or existing.name in ("Unknown", "Dispositivo sin nombre")
                    ):
                        rssi = existing.rssi if existing else None
                        found[address] = BluetoothDevice(
                            address,
                            alias,
                            rssi=rssi,
                            source="bluetoothctl",
                        )

                elif lower_rest.startswith("rssi:"):
                    raw_rssi = rest.split(":", 1)[1].strip()

                    try:
                        rssi = int(raw_rssi)
                    except ValueError:
                        rssi = None

                    if existing is not None:
                        found[address] = BluetoothDevice(
                            existing.address,
                            existing.name,
                            rssi=rssi,
                            source=existing.source,
                        )

                # Todas las demás propiedades CHG se ignoran.
                continue

            # ---------------------------------------------------------
            # [NEW] Device MAC Nombre
            # ---------------------------------------------------------
            if rest:
                if any(lower_rest.startswith(prefix) for prefix in PROPERTY_PREFIXES):
                    # Ejemplo:
                    # Device XX:XX:XX:XX:XX:XX LegacyPairing: no
                    # No es un nombre.
                    continue

                # Evitar que una MAC o su variante con "-" sea nombre.
                normalized_rest = rest.replace("-", ":").upper()

                if re.fullmatch(
                    r"(?:[0-9A-F]{2}:){5}[0-9A-F]{2}",
                    normalized_rest,
                ):
                    name = "Unknown"
                else:
                    name = rest
            else:
                name = "Unknown"

            # Si ya tenemos un nombre real, no lo degradamos.
            if existing is None:
                found[address] = BluetoothDevice(
                    address,
                    name,
                    rssi=None,
                    source="bluetoothctl",
                )
            elif existing.name in ("Unknown", "Dispositivo sin nombre") and name != "Unknown":
                found[address] = BluetoothDevice(
                    address,
                    name,
                    rssi=existing.rssi,
                    source=existing.source,
                )

        return sorted(
            found.values(),
            key=lambda d: (d.name.lower(), d.address),
        )

    def _scan_hcitool(self) -> List[BluetoothDevice]:
        proc = subprocess.run(
            ["hcitool", "scan"],
            capture_output=True,
            text=True,
            timeout=self.scan_seconds + 5,
            check=False,
        )

        if proc.returncode != 0:
            raise RuntimeError(
                proc.stderr.strip() or "hcitool scan failed"
            )

        found = []

        for line in proc.stdout.splitlines():
            match = re.match(
                r"\s*(%s)\s+(.+?)\s*$" % MAC_RE,
                line,
            )

            if match:
                found.append(
                    BluetoothDevice(
                        match.group("mac").upper(),
                        match.group(2).strip() or "Unknown",
                        source="hcitool",
                    )
                )

        return found
