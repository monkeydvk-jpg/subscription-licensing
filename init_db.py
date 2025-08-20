#!/usr/bin/env python3
"""
Database initialization script for Vercel deployment.
This script safely initializes the database tables.
"""
import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, ProgrammingError

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.config import settings
from app.database import Base, engine
from app.models import User, Subscription, License


def init_database():
    """Initialize database tables safely."""
    try:
        print(f"Connecting to database: {settings.effective_database_url[:50]}...")
        
        # Test connection
        with engine.connect() as conn:
            if "postgresql" in settings.effective_database_url:
                result = conn.execute(text("SELECT version()"))
                print(f"PostgreSQL version: {result.fetchone()[0]}")
            else:
                result = conn.execute(text("SELECT sqlite_version()"))
                print(f"SQLite version: {result.fetchone()[0]}")
        
        # Create tables
        print("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created successfully!")
        
        return True
        
    except OperationalError as e:
        print(f"❌ Database connection failed: {e}")
        return False
    except ProgrammingError as e:
        print(f"❌ Database programming error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


if __name__ == "__main__":
    success = init_database()
    sys.exit(0 if success else 1)
