# app/core/database.py
import os
import logging
from typing import Generator
from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.exc import SQLAlchemyError

from . import config  # contains DATABASE_URL

# ---- logging ----
logger = logging.getLogger("app.db")  # use this logger name in logs

# Turn on SQL echo with env var: SQLALCHEMY_ECHO=1
SQL_ECHO = os.getenv("SQLALCHEMY_ECHO", "0") in ("1", "true", "True")

# ---- engine / session / Base ----
engine = create_engine(
    config.DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    echo=SQL_ECHO,  # will print SQL if enabled
    connect_args={"check_same_thread": False} if config.DATABASE_URL.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Optional: log connections being opened
@event.listens_for(engine, "connect")
def _on_connect(dbapi_connection, connection_record):
    logger.info("DB connection opened: %s", engine.url)

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def check_db_connection() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            logger.info("Database connection successful: %s", engine.url)
            return True
    except SQLAlchemyError as e:
        logger.error("Database connection failed: %s", e)
        return False
    except Exception as e:
        logger.error("Unexpected DB error: %s", e)
        return False

def init_db() -> None:
    """
    Import models so they register on Base.metadata, then create tables.
    """
    try:
        logger.info("Importing models and creating tables …")
        from app import models  # <-- IMPORTANT: ensures models are registered on this Base
        Base.metadata.create_all(bind=engine)
        # Log the tables we see on this metadata
        tables = ", ".join(sorted(Base.metadata.tables.keys())) or "(none)"
        logger.info("Tables present: %s", tables)
    except Exception as e:
        logger.error("Failed to create database tables: %s", e)
        raise
