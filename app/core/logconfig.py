# app/core/logconfig.py
import os
import pathlib
from logging.config import dictConfig


def _ensure_logfile(path_str: str) -> str:
    p = pathlib.Path(path_str).expanduser().resolve()
    try:
        p.parent.mkdir(parents=True, exist_ok=True)  # create folder if missing
        p.touch(exist_ok=True)                       # create file if missing
        return str(p)
    except Exception:
        # fallback if the chosen path isn't writable
        fallback = pathlib.Path("/tmp/whatsapp.log")
        fallback.touch(exist_ok=True)
        return str(fallback)


def configure_logging():
    logfile = _ensure_logfile(os.getenv("WHATSAPP_LOG_FILE", "logs/whatsapp.log"))

    dictConfig({
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "std": {"format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"},
        },
        "handlers": {
            "whatsapp_file": {
                "class": "logging.handlers.TimedRotatingFileHandler",
                "filename": logfile,
                "when": "midnight",
                "backupCount": 14,
                "encoding": "utf-8",
                "formatter": "std",
                "level": os.getenv("WHATSAPP_LOG_LEVEL", "INFO").upper(),
            },
        },
        "loggers": {
            "app.whatsapp": {
                "handlers": ["whatsapp_file"],
                "level": os.getenv("WHATSAPP_LOG_LEVEL", "INFO").upper(),
                "propagate": False   # <- prevents console output
            },
        },
        "root": {"handlers": [], "level": "WARNING"},
    })
