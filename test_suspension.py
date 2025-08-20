#!/usr/bin/env python3
"""
Test script to verify license suspension functionality.
"""
import requests
import json

# Configuration
BASE_URL = "http://127.0.0.1:8000"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "changeme"

def get_admin_token():
    """Get admin authentication token."""
    login_data = {
        "username": ADMIN_USERNAME,
        "password": ADMIN_PASSWORD
    }
    
    response = requests.post(
        f"{BASE_URL}/api/admin/login",
        data=login_data
    )
    
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        print(f"Failed to login: {response.status_code}")
        print(response.text)
        return None

def create_test_license(token):
    """Create a test license."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    data = {"email": "test@example.com"}
    
    response = requests.post(
        f"{BASE_URL}/api/admin/licenses",
        headers=headers,
        data=data
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Created test license: {result['license_key']}")
        return result['license_key'], result['license_id']
    else:
        print(f"❌ Failed to create license: {response.status_code}")
        print(response.text)
        return None, None

def validate_license(license_key):
    """Validate a license key."""
    data = {
        "license_key": license_key,
        "extension_version": "1.0.0",
        "device_fingerprint": "test-device"
    }
    
    response = requests.post(
        f"{BASE_URL}/api/validate",
        json=data
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"License validation result: {result}")
        return result
    else:
        print(f"❌ Validation failed: {response.status_code}")
        print(response.text)
        return None

def suspend_license(token, license_id):
    """Suspend a license."""
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.post(
        f"{BASE_URL}/api/admin/licenses/{license_id}/suspend",
        headers=headers
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Suspended license: {result}")
        return True
    else:
        print(f"❌ Failed to suspend license: {response.status_code}")
        print(response.text)
        return False

def create_test_subscription(token, email):
    """Create a test subscription."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    data = {
        "user_email": email,
        "plan_name": "basic",
        "amount": 9.99,
        "status": "active"
    }
    
    response = requests.post(
        f"{BASE_URL}/api/admin/subscriptions",
        headers=headers,
        json=data
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Created test subscription: {result}")
        return result.get("subscription_id")
    else:
        print(f"❌ Failed to create subscription: {response.status_code}")
        print(response.text)
        return None

def main():
    """Test license suspension functionality."""
    print("🧪 Testing License Suspension Functionality")
    print("=" * 50)
    
    # Get admin token
    print("1. Getting admin token...")
    token = get_admin_token()
    if not token:
        return
    
    # Create test subscription first (needed for license validation)
    print("2. Creating test subscription...")
    subscription_id = create_test_subscription(token, "test@example.com")
    if not subscription_id:
        return
    
    # Create test license
    print("3. Creating test license...")
    license_key, license_id = create_test_license(token)
    if not license_key:
        return
    
    # Test 1: Validate license (should be valid)
    print("4. Testing license validation (should be VALID)...")
    result = validate_license(license_key)
    if result:
        if result.get("valid"):
            print("✅ License is valid (as expected)")
        else:
            print(f"❌ License should be valid but got: {result}")
            return
    
    # Test 2: Suspend license
    print("5. Suspending license...")
    if not suspend_license(token, license_id):
        return
    
    # Test 3: Validate suspended license (should be invalid)
    print("6. Testing suspended license validation (should be INVALID)...")
    result = validate_license(license_key)
    if result:
        if not result.get("valid"):
            print(f"✅ Suspended license correctly rejected: {result.get('message')}")
            
            # Check error code (new feature)
            error_code = result.get("error_code")
            if error_code == "SUSPENDED":
                print("✅ Error code correctly indicates SUSPENDED")
            else:
                print(f"⚠️  Error code should be 'SUSPENDED' but got: {error_code}")
            
            # Check if the message indicates suspension (legacy support)
            if "suspended" in result.get("message", "").lower():
                print("✅ Message also indicates suspension (legacy support)")
            else:
                print(f"⚠️  Message doesn't clearly indicate suspension: {result.get('message')}")
        else:
            print(f"❌ Suspended license should be invalid but got: {result}")
    
    print("\n🎉 Test completed!")
    print("\n💡 Instructions for extension (updated with error codes):")
    print("   - Extension should check response.valid === false")
    print("   - Extension should check response.error_code === 'SUSPENDED' (new preferred method)")
    print("   - Extension can fall back to checking response.message contains 'suspended' (legacy)")
    print("   - Extension should handle suspended state by disabling functionality and showing user notice")

if __name__ == "__main__":
    main()
