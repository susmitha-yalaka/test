# app/core/database.py (add/modify parts)

import os
import logging
from typing import Generator, Dict, List, Optional
from sqlalchemy import create_engine, text, event, inspect
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.exc import SQLAlchemyError

from . import config

logger = logging.getLogger("app.db")
SQL_ECHO = os.getenv("SQLALCHEMY_ECHO", "0") in ("1", "true", "True")

engine = create_engine(
    config.DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    echo=SQL_ECHO,
    connect_args={"check_same_thread": False} if config.DATABASE_URL.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

@event.listens_for(engine, "connect")
def _on_connect(dbapi_connection, connection_record):
    logger.info("DB connection opened: %s", engine.url)

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def check_db_connection() -> None:
    with engine.connect() as conn:
        v = conn.execute(
            text("select version(), current_database()")
        ).fetchone()
        logger.info("Connected to: %s | db=%s", v[0], v[1])

def _live_db_objects() -> Dict[str, Dict[str, List[str]]]:
    """
    Return {'schema': {'tables': [...], 'views': [...]}} from the **database**,
    not from SQLAlchemy metadata.
    """
    out: Dict[str, Dict[str, List[str]]] = {}
    with engine.connect() as conn:
        insp = inspect(conn)
        dialect = engine.dialect.name

        # choose relevant schemas
        schemas: List[Optional[str]]
        if dialect == "postgresql":
            current_schema = conn.execute(text("select current_schema()")).scalar() or "public"
            schemas = [current_schema]
        elif dialect in ("mysql", "mariadb"):
            # MySQL treats "schema" ~ database
            schemas = [conn.execute(text("select database()")).scalar()]
        elif dialect == "sqlite":
            schemas = [None]  # SQLite ignores schema
        else:
            schemas = [None]

        for sch in schemas:
            tables = sorted(insp.get_table_names(schema=sch))
            views  = sorted(insp.get_view_names(schema=sch))
            out[sch or "default"] = {"tables": tables, "views": views}
    return out

def init_db() -> None:
    try:
        logger.info("Importing models and creating tables …")
        from app import models  # IMPORTANT: registers models on this Base
        Base.metadata.create_all(bind=engine)

        # Log what the **database** actually has:
        live = _live_db_objects()
        for schema, objs in live.items():
            logger.info("Schema=%s | tables: %s", schema, ", ".join(objs["tables"]) or "(none)")
            if objs["views"]:
                logger.info("Schema=%s | views: %s", schema, ", ".join(objs["views"]))
    except Exception:
        logger.exception("Failed to create database tables")
        raise
