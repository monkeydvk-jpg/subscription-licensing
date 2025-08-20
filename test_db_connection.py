#!/usr/bin/env python3
"""
Test database connection and show configuration
"""
import os
import sys
from sqlalchemy import create_engine, text

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.config import settings

def test_connection():
    """Test database connection and show configuration"""
    
    print("🔍 Database Configuration:")
    print("-" * 50)
    
    # Show environment variables
    db_vars = ['DATABASE_URL', 'POSTGRES_URL', 'POSTGRES_DATABASE_URL', 'NEON_DATABASE_URL']
    for var in db_vars:
        value = os.getenv(var)
        if value:
            print(f"{var}: {value[:50]}{'...' if len(value) > 50 else ''}")
        else:
            print(f"{var}: Not set")
    
    print("-" * 50)
    
    # Get effective database URL
    database_url = settings.effective_database_url
    print(f"🗄️ Effective database URL: {database_url[:50]}{'...' if len(database_url) > 50 else ''}")
    print(f"🔍 Database type: {'PostgreSQL' if 'postgres' in database_url else 'SQLite'}")
    
    # Test connection
    try:
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            print("✅ Database connection successful")
            
            if 'postgres' in database_url:
                # PostgreSQL specific tests
                result = conn.execute(text("SELECT version()"))
                version = result.fetchone()[0]
                print(f"📊 PostgreSQL version: {version}")
                
                # Check if tables exist
                result = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"))
                tables = [row[0] for row in result]
                if tables:
                    print(f"📋 Existing tables: {', '.join(tables)}")
                else:
                    print("📋 No tables found (database is empty)")
            else:
                # SQLite
                print("⚠️ Using SQLite - this will cause issues in production")
                
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    test_connection()
