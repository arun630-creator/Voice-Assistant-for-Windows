"""
Nova Voice Assistant — Centralized Logging
Rotating file + coloured console handler.
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from typing import Optional

from config import LOG_LEVEL, LOG_FORMAT, LOG_FILE, LOG_MAX_BYTES, LOG_BACKUP_COUNT


_INITIALISED: bool = False


def setup_logging() -> None:
    """Initialise root logger once.  Safe to call multiple times."""
    global _INITIALISED
    if _INITIALISED:
        return

    root = logging.getLogger()
    root.setLevel(getattr(logging, LOG_LEVEL, logging.DEBUG))

    formatter = logging.Formatter(LOG_FORMAT)

    # ── Console handler ───────────────────────────────────────────────────
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(formatter)
    root.addHandler(console)

    # ── File handler (rotating) ───────────────────────────────────────────
    try:
        file_handler = RotatingFileHandler(
            str(LOG_FILE),
            maxBytes=LOG_MAX_BYTES,
            backupCount=LOG_BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)
    except OSError as exc:
        root.warning("Could not create log file handler: %s", exc)

    _INITIALISED = True


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Return a named child logger, initialising root if needed."""
    setup_logging()
    return logging.getLogger(name or "nova")
