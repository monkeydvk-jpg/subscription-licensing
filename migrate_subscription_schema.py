#!/usr/bin/env python3
"""
Database migration script to add new columns to subscriptions table.
This script adds the columns needed for enhanced subscription information.
"""

import sqlite3
import sys
import os
from pathlib import Path

def migrate_database():
    """Add new columns to the subscriptions table."""
    
    # Get the database path
    db_path = Path(__file__).parent / "subscriptions.db"
    
    if not db_path.exists():
        print(f"Database file not found: {db_path}")
        print("Creating new database with updated schema...")
        return create_new_database()
    
    print(f"Migrating database: {db_path}")
    
    try:
        # Connect to the database
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Check if the columns already exist
        cursor.execute("PRAGMA table_info(subscriptions)")
        columns = [row[1] for row in cursor.fetchall()]
        print(f"Current columns in subscriptions table: {columns}")
        
        # List of columns to add
        new_columns = [
            ("stripe_price_id", "VARCHAR(255)"),
            ("plan_name", "VARCHAR(100)"),
            ("billing_cycle", "VARCHAR(20)"),
            ("trial_end", "DATETIME"),
            ("end_time", "DATETIME")
        ]
        
        # Add missing columns
        for column_name, column_type in new_columns:
            if column_name not in columns:
                print(f"Adding column: {column_name} {column_type}")
                cursor.execute(f"ALTER TABLE subscriptions ADD COLUMN {column_name} {column_type}")
            else:
                print(f"Column {column_name} already exists, skipping...")
        
        # Commit the changes
        conn.commit()
        print("✅ Database migration completed successfully!")
        
        # Verify the changes
        cursor.execute("PRAGMA table_info(subscriptions)")
        updated_columns = [row[1] for row in cursor.fetchall()]
        print(f"Updated columns in subscriptions table: {updated_columns}")
        
    except sqlite3.Error as e:
        print(f"❌ Database migration failed: {e}")
        return False
    finally:
        if conn:
            conn.close()
    
    return True

def create_new_database():
    """Create a new database with the updated schema."""
    print("Creating new database with updated schema...")
    
    # Import the models and database setup
    sys.path.append(str(Path(__file__).parent))
    
    try:
        from app.database import engine, Base
        from app import models  # This imports all the models
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        print("✅ New database created successfully with updated schema!")
        return True
        
    except Exception as e:
        print(f"❌ Failed to create new database: {e}")
        return False

def verify_migration():
    """Verify that the migration was successful."""
    db_path = Path(__file__).parent / "subscriptions.db"
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Check if all required columns exist
        cursor.execute("PRAGMA table_info(subscriptions)")
        columns = [row[1] for row in cursor.fetchall()]
        
        required_columns = [
            "stripe_price_id", "plan_name", "billing_cycle", "trial_end", "end_time"
        ]
        
        missing_columns = [col for col in required_columns if col not in columns]
        
        if missing_columns:
            print(f"❌ Migration verification failed. Missing columns: {missing_columns}")
            return False
        else:
            print("✅ Migration verification successful. All required columns present.")
            return True
            
    except sqlite3.Error as e:
        print(f"❌ Migration verification failed: {e}")
        return False
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("🚀 Starting database migration...")
    print("=" * 50)
    
    if migrate_database():
        print("=" * 50)
        print("🔍 Verifying migration...")
        if verify_migration():
            print("=" * 50)
            print("🎉 Database migration completed successfully!")
            print("You can now restart your application.")
        else:
            print("⚠️  Migration completed but verification failed.")
            sys.exit(1)
    else:
        print("❌ Migration failed!")
        sys.exit(1)
