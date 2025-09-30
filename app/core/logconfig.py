# app/core/logconfig.py
from __future__ import annotations
import pathlib
from logging.config import dictConfig

# ---- Hardcoded destinations & levels ----
_LOG_FILES = {
    "app.main":               "logs/app_main.log",
    "app.db":                 "logs/app_db.log",
    "flows.boutique":         "logs/flows_boutique.log",
    "routers.webhook":        "logs/webhook.log",
    "services.message_logic": "logs/message_logic.log",
    "app.whatsapp":           "logs/whatsapp.log",
    "routers.products":  "logs/routers_products.log",
    "routers.inventory": "logs/routers_inventory.log",
    "routers.orders":    "logs/routers_orders.log",
}

_LOG_LEVELS = {
    "app.main": "INFO",
    "app.db": "INFO",
    "flows.boutique": "DEBUG",
    "routers.webhook": "INFO",
    "services.message_logic": "INFO",
    "app.whatsapp": "INFO",
    "routers.products":  "INFO",
    "routers.inventory": "INFO",
    "routers.orders":    "INFO",
}


def _ensure(path_str: str) -> str:
    p = pathlib.Path(path_str).expanduser().resolve()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.touch(exist_ok=True)
    return str(p)


def configure_logging() -> None:
    # Handlers: one per logger
    handlers = {}
    for name, path in _LOG_FILES.items():
        hid = f"file__{name.replace('.', '_')}"
        handlers[hid] = {
            "class": "logging.handlers.TimedRotatingFileHandler",
            "filename": _ensure(path),
            "when": "midnight",
            "backupCount": 14,
            "encoding": "utf-8",
            "formatter": "std",
            "level": _LOG_LEVELS.get(name, "INFO"),
        }

    # Loggers wired to their dedicated handler; no propagation to root
    loggers_cfg = {}
    for name in _LOG_FILES.keys():
        hid = f"file__{name.replace('.', '_')}"
        loggers_cfg[name] = {
            "handlers": [hid],
            "level": _LOG_LEVELS.get(name, "INFO"),
            "propagate": False,
        }

    dictConfig({
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "std": {"format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"},
        },
        "handlers": handlers,
        "loggers": loggers_cfg,
        "root": {"handlers": [], "level": "WARNING"},  # keep root silent
    })
