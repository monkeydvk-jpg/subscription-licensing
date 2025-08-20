"""
Database configuration and session management.
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from .config import settings
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Get the effective database URL
DATABASE_URL = settings.effective_database_url
logger.info(f"🗄️ Using database URL: {DATABASE_URL[:50]}{'...' if len(DATABASE_URL) > 50 else ''}")
logger.info(f"🔍 Database type: {'PostgreSQL' if 'postgres' in DATABASE_URL else 'SQLite'}")

# Create database engine
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()


def get_db():
    """Dependency to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Create all database tables."""
    Base.metadata.create_all(bind=engine)
