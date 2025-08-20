"""
Database configuration and session management.
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from .config import settings
import logging
import os

# Configure logging
logger = logging.getLogger(__name__)

# Get the effective database URL
DATABASE_URL = settings.effective_database_url
logger.info(f"🗄️ Using database URL: {DATABASE_URL[:50]}{'...' if len(DATABASE_URL) > 50 else ''}")
logger.info(f"🔍 Database type: {'PostgreSQL' if 'postgres' in DATABASE_URL else 'SQLite'}")

# Debug: Print all environment variables that start with DATABASE or POSTGRES
for key, value in os.environ.items():
    if any(prefix in key.upper() for prefix in ['DATABASE', 'POSTGRES']):
        logger.info(f"🔍 Found env var: {key} = {value[:50]}{'...' if len(value) > 50 else ''}")

# Create database engine with error handling
try:
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
    )
    # Test the connection
    with engine.connect() as conn:
        logger.info("✅ Database connection successful")
except Exception as e:
    logger.error(f"❌ Database connection failed: {e}")
    logger.info("🔄 Falling back to SQLite")
    # Fallback to SQLite
    DATABASE_URL = "sqlite:///./subscriptions.db"
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}
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
