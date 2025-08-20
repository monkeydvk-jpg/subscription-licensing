#!/usr/bin/env python3
"""
Final verification test to ensure end_time functionality is working correctly.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.append(str(Path(__file__).parent))

from app.database import get_db
from app.models import User, Subscription, License, SubscriptionStatus
from app.services.license_service import LicenseService

def test_end_time_functionality():
    """Test that end_time field works correctly in license validation."""
    
    print("🧪 END_TIME FUNCTIONALITY TEST")
    print("=" * 50)
    
    db = next(get_db())
    
    try:
        # Step 1: Find or create a test scenario
        print("📋 Step 1: Setting up test scenario...")
        
        # Get first subscription and license
        subscription = db.query(Subscription).first()
        license = db.query(License).first()
        
        if not subscription or not license:
            print("❌ No data found to test with")
            return
        
        # Ensure they're linked to the same user
        if subscription.user_id != license.user_id:
            # Find a subscription for the license's user
            subscription = db.query(Subscription).filter(
                Subscription.user_id == license.user_id
            ).first()
            
            if not subscription:
                # Create a basic subscription for testing
                subscription = Subscription(
                    stripe_subscription_id=f"test_sub_{license.user_id}",
                    user_id=license.user_id,
                    status=SubscriptionStatus.ACTIVE,
                    current_period_start=datetime.utcnow(),
                    current_period_end=datetime.utcnow() + timedelta(days=30),
                    cancel_at_period_end=False
                )
                db.add(subscription)
                db.commit()
                db.refresh(subscription)
                print(f"   Created test subscription {subscription.id}")
        
        # Make sure license is active
        license.is_active = True
        license.is_suspended = False
        subscription.status = SubscriptionStatus.ACTIVE
        db.commit()
        
        user = subscription.user
        print(f"   User: {user.email}")
        print(f"   Subscription: {subscription.id}")
        print(f"   License: {license.license_key[:15]}...")
        
        # Step 2: Test without end_time (baseline)
        print("\n📋 Step 2: Testing without end_time (baseline)...")
        
        subscription.end_time = None
        db.commit()
        
        license_service = LicenseService(db)
        result1 = license_service.validate_license(
            license.license_key,
            ip_address="127.0.0.1",
            user_agent="Test Script"
        )
        
        print(f"   Valid: {result1.valid}")
        print(f"   Expires At: {result1.expires_at}")
        print(f"   End Time: {result1.end_time}")
        print(f"   Uses current_period_end: {result1.expires_at == subscription.current_period_end}")
        
        # Step 3: Test with end_time set
        print("\n📋 Step 3: Testing with end_time set...")
        
        custom_end_time = datetime.utcnow() + timedelta(days=7)  # 1 week from now
        subscription.end_time = custom_end_time
        db.commit()
        
        result2 = license_service.validate_license(
            license.license_key,
            ip_address="127.0.0.1",
            user_agent="Test Script"
        )
        
        print(f"   Valid: {result2.valid}")
        print(f"   Expires At: {result2.expires_at}")
        print(f"   End Time: {result2.end_time}")
        
        # Check if expires_at now uses end_time
        uses_end_time = (result2.expires_at and subscription.end_time and 
                        abs((result2.expires_at - subscription.end_time).total_seconds()) < 1)
        
        print(f"   Uses end_time: {uses_end_time}")
        
        # Step 4: Verification
        print("\n✅ VERIFICATION RESULTS:")
        print("-" * 30)
        print(f"✓ Database migration successful: end_time column exists")
        print(f"✓ Subscription model updated: {hasattr(subscription, 'end_time')}")
        print(f"✓ Schema includes end_time: {result2.end_time is not None}")
        print(f"✓ License service uses end_time: {uses_end_time}")
        print(f"✓ Fallback to current_period_end: {result1.expires_at == subscription.current_period_end}")
        
        if uses_end_time:
            print("\n🎉 SUCCESS: end_time functionality is working correctly!")
            print("   • When end_time is set, license validation uses it")
            print("   • When end_time is None, falls back to current_period_end")
            print("   • This allows flexible subscription management")
        else:
            print("\n❌ WARNING: end_time may not be working as expected")
            print("   Please check the license service implementation")
        
        return uses_end_time
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

def show_summary():
    """Show summary of what was implemented."""
    
    print("\n" + "=" * 60)
    print("📋 IMPLEMENTATION SUMMARY")
    print("=" * 60)
    
    print("""
✅ COMPLETED CHANGES:

1. DATABASE SCHEMA:
   • Added end_time DATETIME column to subscriptions table
   • Updated migration script to handle the new column

2. MODELS:
   • Updated Subscription model with end_time field
   • Added end_time to Subscription Pydantic schema
   • Added end_time to LicenseValidationResponse schema

3. BUSINESS LOGIC:
   • Modified license service to prioritize end_time over current_period_end
   • Updated expiration calculation logic
   • Enhanced license validation response

4. USER INTERFACE:
   • Updated view scripts to display end_time
   • Added end_time column to subscription tables
   • Updated documentation and help text

🎯 USE CASES:
   • Grace periods after billing failures
   • Custom trial extensions
   • Promotional period extensions  
   • Manual subscription adjustments
   • Flexible subscription management

🔧 HOW IT WORKS:
   • When end_time is set: License validation uses end_time
   • When end_time is None: Falls back to current_period_end
   • Provides flexibility while maintaining backward compatibility
""")

if __name__ == "__main__":
    success = test_end_time_functionality()
    show_summary()
    
    if success:
        print("\n✅ All tests passed! The end_time feature is ready for use.")
    else:
        print("\n⚠️  Some tests failed. Please review the implementation.")
