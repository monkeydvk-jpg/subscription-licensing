#!/usr/bin/env python3

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import get_db
from app.models import AdminUser
from app.security import verify_password, get_password_hash
from app.config import settings
import requests
import subprocess
import time

def test_admin_user():
    """Test admin user credentials"""
    print("=== Testing Admin User ===")
    
    db = next(get_db())
    try:
        admin_user = db.query(AdminUser).filter(AdminUser.username == settings.admin_username).first()
        
        if admin_user:
            print(f"✓ Admin user found: {admin_user.username}")
            print(f"✓ Is active: {admin_user.is_active}")
            
            # Test password verification
            password_valid = verify_password(settings.admin_password, admin_user.hashed_password)
            print(f"✓ Password verification: {password_valid}")
            
            return admin_user, password_valid
        else:
            print("✗ No admin user found")
            return None, False
            
    except Exception as e:
        print(f"✗ Error checking admin user: {e}")
        return None, False
    finally:
        db.close()

def test_login_api():
    """Test login API endpoint"""
    print("\n=== Testing Login API ===")
    
    try:
        # Test login API
        response = requests.post(
            "http://127.0.0.1:8000/api/admin/login",
            data={
                "username": settings.admin_username,
                "password": settings.admin_password
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=5
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Login successful! Token: {data.get('access_token', 'N/A')[:20]}...")
            return True
        else:
            print(f"✗ Login failed with status {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("✗ Cannot connect to server. Is it running?")
        return False
    except Exception as e:
        print(f"✗ Error testing login API: {e}")
        return False

if __name__ == "__main__":
    print("Starting login test...\n")
    
    # Test 1: Check admin user in database
    admin_user, password_valid = test_admin_user()
    
    if not admin_user or not password_valid:
        print("✗ Admin user setup failed. Exiting.")
        sys.exit(1)
    
    print(f"\n✓ Admin credentials: {settings.admin_username} / {settings.admin_password}")
    
    # Test 2: Test login API
    if test_login_api():
        print("\n✅ All tests passed!")
    else:
        print("\n❌ Login API test failed!")
        
        print("\nTry these steps:")
        print("1. Make sure the server is running: uvicorn app.main:app --reload")
        print("2. Check server logs for errors")
        print("3. Try accessing http://127.0.0.1:8000/docs to verify server is up")
