from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
import logging
from typing import Generator

from . import config

# Configure logging
logger = logging.getLogger(__name__)

# Create SQLAlchemy engine
engine = create_engine(
    config.DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300
)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class for models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency to get database session.
    Yields a database session and ensures it's closed after use.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connection() -> bool:
    """
    Check if database connection is working.
    Returns True if connection is successful, False otherwise.
    """
    try:
        with engine.connect() as connection:
            # Execute a simple query to test connection
            result = connection.execute(text("SELECT 1"))
            result.fetchone()
            logger.info("Database connection successful")
            return True
    except SQLAlchemyError as e:
        logger.error(f"Database connection failed: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during database connection test: {e}")
        return False


def init_db() -> None:
    """
    Initialize database tables.
    Creates all tables defined in the models.
    """
    try:
        # Import all models to ensure they are registered with Base
        from app.models import user, restaurant, menu, order  # noqa: F401

        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise


def drop_db() -> None:
    """
    Drop all database tables.
    WARNING: This will delete all data!
    """
    try:
        # Import all models to ensure they are registered with Base
        from app.models import user, restaurant, menu, order  # noqa: F401

        # Drop all tables
        Base.metadata.drop_all(bind=engine)
        logger.info("Database tables dropped successfully")
    except Exception as e:
        logger.error(f"Failed to drop database tables: {e}")
        raise


def reset_db() -> None:
    """
    Reset database by dropping and recreating all tables.
    WARNING: This will delete all data!
    """
    try:
        drop_db()
        init_db()
        logger.info("Database reset successfully")
    except Exception as e:
        logger.error(f"Failed to reset database: {e}")
        raise
