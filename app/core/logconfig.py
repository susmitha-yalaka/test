# app/core/logconfig.py
from logging.config import dictConfig


def configure_logging():
    dictConfig({
        "version": 1,
        "disable_existing_loggers": False,   # keep uvicorn’s own loggers
        "formatters": {
            "std": {"format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"},
        },
        "handlers": {
            "whatsapp_file": {
                "class": "logging.handlers.TimedRotatingFileHandler",
                "filename": "logs/whatsapp.log",
                "when": "midnight",
                "backupCount": 14,
                "encoding": "utf-8",
                "formatter": "std",
                "level": "INFO",
            },
            # add other file handlers if you need separate files:
            # "db_file": {...}
        },
        "loggers": {
            # <-- OUR logger: does NOT propagate to root (no console)
            "app.whatsapp": {
                "handlers": ["whatsapp_file"],
                "level": "INFO",
                "propagate": False
            },
            # example if you added a DB logger:
            # "app.db": {"handlers": ["db_file"], "level": "INFO", "propagate": False},
        },
        # root logger gets NO handlers here; uvicorn config will still manage its own
        "root": {"handlers": [], "level": "WARNING"},
    })
