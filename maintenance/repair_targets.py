#!/usr/bin/env python3
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config import load_config
from storage.repository import TargetRepository


def main():
    cfg = load_config()
    repo = TargetRepository(cfg.database_path)
    changed = repo.repair_placeholders()
    print(f"Reparados: {changed}")


if __name__ == "__main__":
    main()
