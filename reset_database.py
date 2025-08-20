#!/usr/bin/env python3
"""
Database reset script for PostgreSQL
This script will drop all tables and recreate them fresh.
"""
import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.config import settings
from app.models import Base

def reset_database():
    """Reset the database to a clean state"""
    
    # Get the database URL
    database_url = settings.effective_database_url
    print(f"🗄️ Using database URL: {database_url[:50]}{'...' if len(database_url) > 50 else ''}")
    
    if 'sqlite' in database_url.lower():
        print("❌ Error: Still using SQLite. PostgreSQL environment variable not set properly.")
        print("Please check your DATABASE_URL environment variable.")
        return False
    
    try:
        # Create engine
        engine = create_engine(database_url)
        
        print("🔄 Connecting to PostgreSQL database...")
        
        # Test connection
        with engine.connect() as conn:
            print("✅ Database connection successful")
            
            # Drop all tables
            print("🗑️ Dropping all existing tables...")
            Base.metadata.drop_all(bind=engine)
            print("✅ All tables dropped")
            
            # Create all tables fresh
            print("🏗️ Creating fresh database schema...")
            Base.metadata.create_all(bind=engine)
            print("✅ Database schema created successfully")
            
            # Test table creation
            result = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"))
            tables = [row[0] for row in result]
            print(f"📊 Created tables: {', '.join(tables)}")
            
        print("🎉 Database reset completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Database reset failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting database reset...")
    success = reset_database()
    if success:
        print("✅ Database is now ready for use")
    else:
        print("❌ Database reset failed")
        sys.exit(1)
