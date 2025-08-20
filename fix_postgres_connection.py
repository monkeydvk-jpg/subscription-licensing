#!/usr/bin/env python3
"""
Script to test and fix PostgreSQL connection issues.
This script will try to connect to PostgreSQL using various environment variables
and reset the database if needed.
"""
import os
import sys
from datetime import datetime
from sqlalchemy import create_engine, text, MetaData
from sqlalchemy.orm import sessionmaker

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

def find_postgres_url():
    """Find PostgreSQL URL from environment variables."""
    
    # List of possible PostgreSQL environment variable names
    possible_vars = [
        'POSTGRES_URL',
        'POSTGRES_DATABASE_URL', 
        'NEON_DATABASE_URL',
        'DATABASE_URL',
        'DATABASE_URL_POSTGRES_URL',
        'DATABASE_URL_DATABASE_URL',
        'DATABASE_URL_POSTGRES_PRISMA_URL',
        'DATABASE_URL_POSTGRES_URL_NON_POOLING',
        'POSTGRES_PRISMA_URL',
        'POSTGRES_URL_NON_POOLING'
    ]
    
    print("🔍 Searching for PostgreSQL connection string...")
    
    for var_name in possible_vars:
        value = os.getenv(var_name)
        if value and ('postgresql://' in value or 'postgres://' in value):
            print(f"✅ Found PostgreSQL URL in {var_name}: {value[:50]}...")
            return value
    
    print("❌ No PostgreSQL URL found in environment variables.")
    print("Available environment variables:")
    for key, value in os.environ.items():
        if any(prefix in key.upper() for prefix in ['DATABASE', 'POSTGRES']):
            print(f"  {key}: {value[:50]}{'...' if len(value) > 50 else ''}")
    
    return None

def test_postgres_connection(database_url):
    """Test PostgreSQL connection and return engine if successful."""
    
    try:
        print(f"🔗 Testing connection to: {database_url[:50]}...")
        
        engine = create_engine(database_url)
        
        # Test the connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"✅ PostgreSQL connection successful!")
            print(f"📊 PostgreSQL version: {version[:100]}")
            
            # Check existing tables
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """))
            tables = [row[0] for row in result]
            
            if tables:
                print(f"📋 Existing tables: {', '.join(tables)}")
            else:
                print("📋 No tables found - database is empty")
            
            return engine
            
    except Exception as e:
        print(f"❌ PostgreSQL connection failed: {e}")
        return None

def create_tables_in_postgres(engine):
    """Create all tables in PostgreSQL database."""
    
    try:
        from app.models import Base
        
        print("🔨 Creating database tables...")
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created successfully!")
        
        # Verify tables were created
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """))
            tables = [row[0] for row in result]
            print(f"📋 Created tables: {', '.join(tables)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to create tables: {e}")
        return False

def create_admin_user(engine):
    """Create default admin user."""
    
    try:
        from app.models import AdminUser
        from app.security import get_password_hash
        
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        try:
            # Check if admin user already exists
            admin_user = db.query(AdminUser).filter(AdminUser.username == "admin").first()
            
            if not admin_user:
                admin_user = AdminUser(
                    username="admin",
                    hashed_password=get_password_hash("changeme"),
                    is_active=True
                )
                db.add(admin_user)
                db.commit()
                print("✅ Created default admin user (admin/changeme)")
            else:
                print("ℹ️ Admin user already exists")
                
            return True
            
        finally:
            db.close()
            
    except Exception as e:
        print(f"❌ Failed to create admin user: {e}")
        return False

def main():
    """Main function to fix PostgreSQL connection."""
    
    print("🚀 PostgreSQL Connection Fix Script")
    print("=" * 50)
    
    # Find PostgreSQL URL
    postgres_url = find_postgres_url()
    if not postgres_url:
        print("❌ Cannot proceed without PostgreSQL URL")
        return False
    
    # Test connection
    engine = test_postgres_connection(postgres_url)
    if not engine:
        print("❌ Cannot proceed without working PostgreSQL connection")
        return False
    
    # Create tables
    if not create_tables_in_postgres(engine):
        print("❌ Failed to create database tables")
        return False
    
    # Create admin user
    if not create_admin_user(engine):
        print("❌ Failed to create admin user")
        return False
    
    print("\n✅ PostgreSQL database setup completed successfully!")
    print("🎉 Your app should now use PostgreSQL instead of SQLite")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
