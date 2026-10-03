import unittest

from bluetooth.scanner import BluetoothScanner
from storage.repository import is_placeholder_name


class TestBluetoothParser(unittest.TestCase):
    def test_new_and_changed_name(self):
        lines = [
            "[NEW] Device AA:BB:CC:DD:EE:FF",
            "[CHG] Device AA:BB:CC:DD:EE:FF RSSI: -57",
            "[CHG] Device AA:BB:CC:DD:EE:FF Name: My Speaker",
            "[CHG] Device AA:BB:CC:DD:EE:FF LegacyPairing: no",
        ]
        devices = BluetoothScanner._parse_bluetoothctl(lines)
        self.assertEqual(len(devices), 1)
        self.assertEqual(devices[0].name, "My Speaker")
        self.assertEqual(devices[0].rssi, -57)

    def test_unknown_name_is_not_mac(self):
        lines = ["[NEW] Device 11:22:33:44:55:66"]
        devices = BluetoothScanner._parse_bluetoothctl(lines)
        self.assertEqual(len(devices), 1)
        self.assertEqual(devices[0].name, "Unknown")
        self.assertTrue(is_placeholder_name(devices[0].name, devices[0].address))

    def test_property_line_never_becomes_name(self):
        lines = [
            "[NEW] Device 22:33:44:55:66:77 LegacyPairing: no",
            "[CHG] Device 22:33:44:55:66:77 RSSI: -88",
        ]
        devices = BluetoothScanner._parse_bluetoothctl(lines)
        self.assertEqual(len(devices), 1)
        self.assertEqual(devices[0].name, "Unknown")


if __name__ == "__main__":
    unittest.main()
