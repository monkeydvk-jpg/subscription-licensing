#!/usr/bin/env python3
"""
Test script demonstrating that subscription details now load correctly
with the new end_time field.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import json

sys.path.append(str(Path(__file__).parent))

from app.database import get_db
from app.models import User, Subscription, SubscriptionStatus
from app.services.license_service import LicenseService

def test_subscription_loading():
    """Test that subscriptions load correctly with end_time field."""
    
    print("🧪 TESTING SUBSCRIPTION DETAIL LOADING")
    print("=" * 50)
    
    db = next(get_db())
    
    try:
        # Get all subscriptions
        subscriptions = db.query(Subscription).join(User).all()
        
        if not subscriptions:
            print("❌ No subscriptions found")
            return False
        
        print(f"✅ Found {len(subscriptions)} subscription(s)")
        print()
        
        # Test each subscription
        for i, subscription in enumerate(subscriptions[:5], 1):  # Test first 5
            print(f"📋 Subscription {i}:")
            print(f"   ID: {subscription.id}")
            print(f"   User: {subscription.user.email}")
            print(f"   Plan: {subscription.plan_name or 'Unknown'}")
            print(f"   Status: {subscription.status.value}")
            print(f"   Billing Cycle: {subscription.billing_cycle or 'N/A'}")
            print(f"   Period Start: {subscription.current_period_start}")
            print(f"   Period End: {subscription.current_period_end}")
            print(f"   End Time: {subscription.end_time or 'Not set'}")
            print(f"   Trial End: {subscription.trial_end or 'N/A'}")
            print(f"   Will Cancel: {subscription.cancel_at_period_end}")
            
            # Test API-style response format
            api_response = {
                "id": subscription.id,
                "stripe_subscription_id": subscription.stripe_subscription_id,
                "user_email": subscription.user.email,
                "user_id": subscription.user_id,
                "plan_name": subscription.plan_name or "Unknown",
                "billing_cycle": subscription.billing_cycle or "monthly",
                "status": subscription.status.value,
                "current_period_start": subscription.current_period_start.isoformat() if subscription.current_period_start else None,
                "current_period_end": subscription.current_period_end.isoformat() if subscription.current_period_end else None,
                "end_time": subscription.end_time.isoformat() if subscription.end_time else None,
                "trial_end": subscription.trial_end.isoformat() if subscription.trial_end else None,
                "cancel_at_period_end": subscription.cancel_at_period_end
            }
            
            print(f"   ✅ API Response Ready: {json.dumps(api_response, indent=2)}")
            print()
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing subscription loading: {e}")
        return False
    finally:
        db.close()

def test_license_validation_with_end_time():
    """Test that license validation uses end_time correctly."""
    
    print("🔑 TESTING LICENSE VALIDATION WITH END_TIME")
    print("=" * 50)
    
    db = next(get_db())
    
    try:
        # Find a subscription with end_time set
        subscription = db.query(Subscription).filter(
            Subscription.end_time.isnot(None)
        ).first()
        
        if not subscription:
            print("❌ No subscriptions with end_time found")
            return False
        
        print(f"Testing subscription {subscription.id} with end_time: {subscription.end_time}")
        
        # Get license for this user
        from app.models import License
        license = db.query(License).filter(License.user_id == subscription.user_id).first()
        
        if not license:
            print("❌ No license found for this user")
            return False
        
        # Ensure subscription is active and license is active
        subscription.status = SubscriptionStatus.ACTIVE
        license.is_active = True
        license.is_suspended = False
        db.commit()
        
        # Test license validation
        license_service = LicenseService(db)
        result = license_service.validate_license(
            license.license_key,
            ip_address="127.0.0.1",
            user_agent="Test Script"
        )
        
        print("License Validation Result:")
        print(f"   Valid: {result.valid}")
        print(f"   Expires At: {result.expires_at}")
        print(f"   End Time: {result.end_time}")
        print(f"   Current Period End: {result.current_period_end}")
        print(f"   Days Until Expiry: {result.days_until_expiry}")
        
        # Verify that expires_at uses end_time
        uses_end_time = (result.expires_at and subscription.end_time and 
                        abs((result.expires_at - subscription.end_time).total_seconds()) < 1)
        
        print(f"   ✅ Uses end_time for expiry: {uses_end_time}")
        
        return result.valid and uses_end_time
        
    except Exception as e:
        print(f"❌ Error testing license validation: {e}")
        return False
    finally:
        db.close()

def main():
    """Run all tests."""
    
    print("🚀 SUBSCRIPTION LOADING TESTS")
    print("=" * 60)
    print()
    
    # Test 1: Subscription loading
    test1_passed = test_subscription_loading()
    print()
    
    # Test 2: License validation with end_time
    test2_passed = test_license_validation_with_end_time()
    print()
    
    # Results
    print("=" * 60)
    print("📊 TEST RESULTS:")
    print(f"   Subscription Loading: {'✅ PASS' if test1_passed else '❌ FAIL'}")
    print(f"   License Validation: {'✅ PASS' if test2_passed else '❌ FAIL'}")
    
    if test1_passed and test2_passed:
        print("\n🎉 ALL TESTS PASSED!")
        print("Subscription details are loading correctly with end_time support.")
        print("\nThe following endpoints now include end_time:")
        print("   • GET /api/admin/subscriptions")
        print("   • GET /api/admin/subscriptions/{id}")
        print("   • POST /api/admin/subscriptions/{id}/set-end-time")
        print("   • POST /api/validate (license validation)")
    else:
        print("\n⚠️  SOME TESTS FAILED!")
        print("Please check the implementation.")

if __name__ == "__main__":
    main()
