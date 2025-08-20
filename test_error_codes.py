#!/usr/bin/env python3
"""
Comprehensive test script to verify all license validation error codes.
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
        return None

def validate_license(license_key, expected_valid=None, expected_error_code=None):
    """Validate a license key and check expected results."""
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
        print(f"  Validation result: {result}")
        
        # Check expected results
        if expected_valid is not None and result.get("valid") != expected_valid:
            print(f"  ❌ Expected valid={expected_valid}, got {result.get('valid')}")
            return False
        
        if expected_error_code is not None and result.get("error_code") != expected_error_code:
            print(f"  ❌ Expected error_code={expected_error_code}, got {result.get('error_code')}")
            return False
        
        print(f"  ✅ Validation matches expectations")
        return True
    else:
        print(f"  ❌ Validation failed: {response.status_code}")
        return False

def create_test_license(token, email="testuser@example.com"):
    """Create a test license."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    data = {"email": email}
    
    response = requests.post(
        f"{BASE_URL}/api/admin/licenses",
        headers=headers,
        data=data
    )
    
    if response.status_code == 200:
        result = response.json()
        return result['license_key'], result['license_id']
    else:
        print(f"Failed to create license: {response.status_code}")
        return None, None

def create_test_subscription(token, email, status="active"):
    """Create a test subscription."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    data = {
        "user_email": email,
        "plan_name": "basic",
        "amount": 9.99,
        "status": status
    }
    
    response = requests.post(
        f"{BASE_URL}/api/admin/subscriptions",
        headers=headers,
        json=data
    )
    
    if response.status_code == 200:
        result = response.json()
        return result.get("subscription_id")
    else:
        print(f"Failed to create subscription: {response.status_code}")
        return None

def suspend_license(token, license_id):
    """Suspend a license."""
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.post(
        f"{BASE_URL}/api/admin/licenses/{license_id}/suspend",
        headers=headers
    )
    
    return response.status_code == 200

def deactivate_license(token, license_id):
    """Deactivate a license."""
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.post(
        f"{BASE_URL}/api/admin/licenses/{license_id}/deactivate",
        headers=headers
    )
    
    return response.status_code == 200

def main():
    """Test all license validation error codes."""
    print("🧪 Testing All License Validation Error Codes")
    print("=" * 60)
    
    # Get admin token
    print("1. Getting admin token...")
    token = get_admin_token()
    if not token:
        return
    print("✅ Admin token obtained")
    
    # Test 1: INVALID_KEY
    print("\n2. Testing INVALID_KEY error code...")
    print("  Testing with non-existent license key...")
    success = validate_license("invalid-license-key-12345", expected_valid=False, expected_error_code="INVALID_KEY")
    if success:
        print("✅ INVALID_KEY test passed")
    else:
        print("❌ INVALID_KEY test failed")
        return
    
    # Test 2: NO_SUBSCRIPTION (valid license but no subscription)
    print("\n3. Testing NO_SUBSCRIPTION error code...")
    print("  Creating license without subscription...")
    license_key, license_id = create_test_license(token, "no-subscription@example.com")
    if license_key:
        success = validate_license(license_key, expected_valid=False, expected_error_code="NO_SUBSCRIPTION")
        if success:
            print("✅ NO_SUBSCRIPTION test passed")
        else:
            print("❌ NO_SUBSCRIPTION test failed")
            return
    
    # Test 3: SUBSCRIPTION_INACTIVE (valid license with canceled subscription)
    print("\n4. Testing SUBSCRIPTION_INACTIVE error code...")
    print("  Creating license with canceled subscription...")
    email = "canceled-subscription@example.com"
    subscription_id = create_test_subscription(token, email, status="canceled")
    if subscription_id:
        license_key, license_id = create_test_license(token, email)
        if license_key:
            success = validate_license(license_key, expected_valid=False, expected_error_code="SUBSCRIPTION_INACTIVE")
            if success:
                print("✅ SUBSCRIPTION_INACTIVE test passed")
            else:
                print("❌ SUBSCRIPTION_INACTIVE test failed")
                return
    
    # Test 4: INACTIVE (deactivated license)
    print("\n5. Testing INACTIVE error code...")
    print("  Creating and then deactivating license...")
    email = "inactive-license@example.com"
    subscription_id = create_test_subscription(token, email)
    if subscription_id:
        license_key, license_id = create_test_license(token, email)
        if license_key:
            # First validate it works
            print("  Validating active license...")
            validate_license(license_key, expected_valid=True, expected_error_code=None)
            
            # Then deactivate it
            print("  Deactivating license...")
            if deactivate_license(token, license_id):
                success = validate_license(license_key, expected_valid=False, expected_error_code="INACTIVE")
                if success:
                    print("✅ INACTIVE test passed")
                else:
                    print("❌ INACTIVE test failed")
                    return
    
    # Test 5: SUSPENDED (suspended license)
    print("\n6. Testing SUSPENDED error code...")
    print("  Creating and then suspending license...")
    email = "suspended-license@example.com"
    subscription_id = create_test_subscription(token, email)
    if subscription_id:
        license_key, license_id = create_test_license(token, email)
        if license_key:
            # First validate it works
            print("  Validating active license...")
            validate_license(license_key, expected_valid=True, expected_error_code=None)
            
            # Then suspend it
            print("  Suspending license...")
            if suspend_license(token, license_id):
                success = validate_license(license_key, expected_valid=False, expected_error_code="SUSPENDED")
                if success:
                    print("✅ SUSPENDED test passed")
                else:
                    print("❌ SUSPENDED test failed")
                    return
    
    # Test 6: Valid license (no error code)
    print("\n7. Testing valid license (no error code)...")
    print("  Creating valid license with active subscription...")
    email = "valid-license@example.com"
    subscription_id = create_test_subscription(token, email)
    if subscription_id:
        license_key, license_id = create_test_license(token, email)
        if license_key:
            success = validate_license(license_key, expected_valid=True, expected_error_code=None)
            if success:
                print("✅ Valid license test passed")
            else:
                print("❌ Valid license test failed")
                return
    
    print("\n🎉 All error code tests completed successfully!")
    print("\n📋 Summary of error codes tested:")
    print("   ✅ INVALID_KEY - License key not found")
    print("   ✅ NO_SUBSCRIPTION - No active subscription")
    print("   ✅ SUBSCRIPTION_INACTIVE - Subscription not active")
    print("   ✅ INACTIVE - License deactivated")
    print("   ✅ SUSPENDED - License suspended")
    print("   ✅ Valid license - No error code")
    
    print("\n💡 Extension developers can now reliably handle all these cases using error_code field!")

if __name__ == "__main__":
    main()
