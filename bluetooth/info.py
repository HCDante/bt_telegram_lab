import re
import shutil
import subprocess
import time
from typing import Dict, Optional

from core.models import BluetoothDevice

MAC_RE = re.compile(r"^(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$")
INFO_KEYS = {
    "Name",
    "Alias",
    "Class",
    "Icon",
    "Paired",
    "Bonded",
    "Trusted",
    "Blocked",
    "Connected",
    "LegacyPairing",
    "RSSI",
    "TxPower",
    "ServicesResolved",
    "WakeAllowed",
}


class BluetoothInfo:
    @staticmethod
    def get(
        address: str,
        scan_seconds: int = 4,
        fallback: Optional[BluetoothDevice] = None,
    ) -> Dict[str, str]:
        """Return BlueZ info for an unpaired or recently discovered device.

        BlueZ may remove Device objects discovered during a scan when the scan
        session ends unless the device is connected/paired. Therefore we keep
        the bluetoothctl process alive, start a short discovery, then ask for
        info for the selected address before stopping discovery.
        """
        address = address.strip().upper()
        if not MAC_RE.fullmatch(address):
            raise ValueError(f"Invalid Bluetooth address: {address}")

        if shutil.which("bluetoothctl"):
            try:
                data = BluetoothInfo._get_via_live_scan(address, max(3, scan_seconds))
                if data:
                    return data
            except Exception:
                # Fall back to last scan data instead of breaking the Telegram flow.
                pass

        if fallback is not None:
            data: Dict[str, str] = {
                "Address": fallback.address,
                "Name": fallback.name,
                "Source": "last scan",
                "BlueZ": "Device object not currently available",
            }
            if fallback.rssi is not None:
                data["RSSI"] = str(fallback.rssi)
            return data

        return {
            "Address": address,
            "BlueZ": "Device object not currently available",
        }

    @staticmethod
    def _get_via_live_scan(address: str, scan_seconds: int) -> Dict[str, str]:
        proc = subprocess.Popen(
            ["bluetoothctl"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        try:
            assert proc.stdin is not None
            proc.stdin.write("power on\n")
            proc.stdin.write("scan on\n")
            proc.stdin.flush()

            # Keep the same bluetoothctl session alive while discovery runs.
            time.sleep(scan_seconds)

            proc.stdin.write(f"info {address}\n")
            proc.stdin.write("scan off\n")
            proc.stdin.write("quit\n")
            proc.stdin.flush()

            stdout, _ = proc.communicate(timeout=8)
            return BluetoothInfo._parse_info(stdout, address)
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait(timeout=2)

    @staticmethod
    def _parse_info(output: str, address: str) -> Dict[str, str]:
        data: Dict[str, str] = {}
        target_seen = False

        for raw in output.splitlines():
            line = raw.strip()
            if not line:
                continue

            m = re.search(rf"Device\s+{re.escape(address)}\b", line, re.I)
            if m:
                target_seen = True
                data["Address"] = address
                continue

            if not target_seen:
                continue

            if ":" not in line:
                continue

            key, value = line.split(":", 1)
            key = key.strip().lstrip("[CHG] ")
            value = value.strip()

            # UUID lines and other free-form BlueZ fields are useful too.
            if key in INFO_KEYS or key == "UUID":
                data[key] = value

        return data
