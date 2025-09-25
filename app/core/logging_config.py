# app/core/logging_config.py
import os
import logging
from logging.handlers import TimedRotatingFileHandler


def setup_whatsapp_logging(level: int | None = None) -> logging.Logger:
    """
    Creates a dedicated rotating file logger for WhatsApp traffic.
    File: logs/whatsapp.log (rotates nightly, 14 backups).
    """
    os.makedirs("logs", exist_ok=True)

    logger = logging.getLogger("app.whatsapp")
    if logger.handlers:
        return logger  # already configured

    # Default to INFO unless overridden by env or arg
    lvl = level or getattr(logging, os.getenv("WHATSAPP_LOG_LEVEL", "INFO").upper(), logging.INFO)
    logger.setLevel(lvl)

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    fh = TimedRotatingFileHandler("logs/whatsapp.log", when="midnight", backupCount=14, encoding="utf-8")
    fh.setLevel(lvl)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    # Avoid duplicating to root/console
    logger.propagate = False
    return logger
