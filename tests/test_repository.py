import os
import tempfile
import unittest

from core.models import BluetoothDevice
from storage.repository import TargetRepository, is_placeholder_name


class TestTargetRepository(unittest.TestCase):
    def test_placeholder_does_not_overwrite_good_name(self):
        with tempfile.TemporaryDirectory() as td:
            db = os.path.join(td, "targets.db")
            repo = TargetRepository(db)
            repo.upsert(BluetoothDevice("AA:BB:CC:DD:EE:FF", "My Speaker"), "t1")
            repo.upsert(BluetoothDevice("AA:BB:CC:DD:EE:FF", "Unknown"), "t2")
            item = repo.get("AA:BB:CC:DD:EE:FF")
            self.assertEqual(item.name, "My Speaker")

    def test_mac_and_legacy_names_are_placeholders(self):
        self.assertTrue(is_placeholder_name("AA:BB:CC:DD:EE:FF", "AA:BB:CC:DD:EE:FF"))
        self.assertTrue(is_placeholder_name("AA-BB-CC-DD-EE-FF", "AA:BB:CC:DD:EE:FF"))
        self.assertTrue(is_placeholder_name("LegacyPairing: no"))


if __name__ == "__main__":
    unittest.main()
