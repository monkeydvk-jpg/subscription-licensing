"""
Database configuration and session management.
"""
from sqlalchemy import create_engine, text
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

# Database connection will be initialized on first request
engine = None

def get_engine():
    """Get database engine, initializing if necessary"""
    global engine
    if engine is None:
        engine = initialize_database()
    return engine

def initialize_database():
    """Initialize database connection with proper error handling"""
    database_url = settings.effective_database_url
    logger.info(f"🗄️ Initializing database: {database_url[:50]}{'...' if len(database_url) > 50 else ''}")
    logger.info(f"🔍 Database type: {'PostgreSQL' if 'postgres' in database_url else 'SQLite'}")
    
    # Debug: Print all environment variables that start with DATABASE or POSTGRES
    postgres_env_vars = {}
    for key, value in os.environ.items():
        if any(prefix in key.upper() for prefix in ['DATABASE', 'POSTGRES']):
            postgres_env_vars[key] = value[:50] + ('...' if len(value) > 50 else '')
            
    if postgres_env_vars:
        logger.info(f"🔍 PostgreSQL environment variables: {postgres_env_vars}")
    else:
        logger.warning("⚠️ No PostgreSQL environment variables found!")
    
    try:
        # Create engine with connection pooling for PostgreSQL
        if 'postgres' in database_url:
            engine = create_engine(
                database_url,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True,  # Verify connections before use
                pool_recycle=300  # Recycle connections every 5 minutes
            )
        else:
            engine = create_engine(
                database_url,
                connect_args={"check_same_thread": False}
            )
        
        # Test the connection
        with engine.connect() as conn:
            logger.info("✅ Database connection successful")
            if 'postgres' in database_url:
                # Test PostgreSQL specific features
                result = conn.execute(text("SELECT version()"))
                version = result.fetchone()[0]
                logger.info(f"📊 PostgreSQL version: {version[:100]}")
                
                # Check if tables exist
                result = conn.execute(text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                """))
                tables = [row[0] for row in result]
                if tables:
                    logger.info(f"📋 Existing tables: {', '.join(tables)}")
                else:
                    logger.info("📋 Database is empty - tables will be created")
                    
            return engine
            
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        
        # If PostgreSQL was attempted, don't fall back to SQLite in production
        if 'postgres' in database_url:
            logger.error("💥 PostgreSQL connection failed - NOT falling back to SQLite in production")
            logger.error("🔧 Please check your PostgreSQL environment variables and connection string")
            raise Exception(f"PostgreSQL connection failed: {e}")
        
        # Only fall back to SQLite for local development
        logger.info("🔄 Falling back to SQLite (THIS WILL CAUSE WRITE ERRORS IN PRODUCTION)")
        
        fallback_url = "sqlite:///./subscriptions.db"
        try:
            engine = create_engine(
                fallback_url,
                connect_args={"check_same_thread": False}
            )
            logger.warning("⚠️ Using SQLite fallback - write operations will fail in serverless environment")
            return engine
        except Exception as fallback_error:
            logger.error(f"❌ Even SQLite fallback failed: {fallback_error}")
            raise

# Create base class for models
Base = declarative_base()


def get_db():
    """Dependency to get database session."""
    # Get the engine and create a session factory dynamically
    engine = get_engine()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Create all database tables."""
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
