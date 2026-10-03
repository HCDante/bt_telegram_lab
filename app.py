#!/usr/bin/env python3
import logging

from config import load_config
from core.controller import Controller
from bot.telegram_bot import TelegramBot


def main() -> None:
    cfg = load_config()
    logging.basicConfig(
        level=getattr(logging, cfg.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    controller = Controller(cfg)
    bot = TelegramBot(cfg, controller)
    bot.run()


if __name__ == "__main__":
    main()
