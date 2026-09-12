"""Centralized logging for Stone FFA Discord bot."""

from __future__ import annotations

import logging
import sys
from typing import Optional

from bot.config import config


def setup_logging(level: Optional[str] = None) -> logging.Logger:
    """Configure root logger and return the bot logger."""
    log_level = (level or config.log_level).upper()
    numeric = getattr(logging, log_level, logging.INFO)

    root = logging.getLogger()
    root.setLevel(numeric)

    # Avoid duplicate handlers on reload
    if not root.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(numeric)
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        root.addHandler(handler)

    # Quiet noisy libraries
    logging.getLogger("discord").setLevel(logging.WARNING)
    logging.getLogger("discord.http").setLevel(logging.WARNING)
    logging.getLogger("aiosqlite").setLevel(logging.WARNING)

    logger = logging.getLogger("stoneffa")
    logger.setLevel(numeric)
    return logger


logger = setup_logging()
