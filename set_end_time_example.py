#!/usr/bin/env python3
"""
Example script showing how to set the end_time field on subscriptions.
This demonstrates using the new end_time field that overrides the current_period_end.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
sys.path.append(str(Path(__file__).parent))

from app.database import get_db
from app.models import User, Subscription

def set_subscription_end_time():
    """Example of setting a custom end_time for a subscription."""
    
    print("🕐 SETTING SUBSCRIPTION END TIME EXAMPLE")
    print("=" * 60)
    
    db = next(get_db())
    
    try:
        # Find the first active subscription
        subscription = db.query(Subscription).filter(
            Subscription.status.in_(['active', 'trialing'])
        ).first()
        
        if not subscription:
            print("❌ No active subscriptions found to demo with")
            return
        
        user = subscription.user
        
        print(f"📋 Original Subscription Details:")
        print(f"   User: {user.email}")
        print(f"   Plan: {subscription.plan_name}")
        print(f"   Status: {subscription.status.value}")
        print(f"   Current Period End: {subscription.current_period_end}")
        print(f"   End Time: {subscription.end_time or 'Not set'}")
        
        # Set a custom end time (e.g., 2 weeks from now)
        custom_end_time = datetime.utcnow() + timedelta(days=14)
        subscription.end_time = custom_end_time
        
        db.commit()
        db.refresh(subscription)
        
        print(f"\n✅ Updated Subscription:")
        print(f"   Current Period End: {subscription.current_period_end}")
        print(f"   End Time: {subscription.end_time}")
        
        print(f"\n💡 Impact:")
        print(f"   • License validation will now use end_time ({subscription.end_time})")
        print(f"   • Instead of current_period_end ({subscription.current_period_end})")
        print(f"   • This allows for custom subscription durations independent of billing cycles")
        
        # Test what the license service would return
        from app.services.license_service import LicenseService
        license_service = LicenseService(db)
        
        # Get a license for this user
        from app.models import License
        license = db.query(License).filter(License.user_id == user.id).first()
        
        if license:
            result = license_service.validate_license(
                license.license_key,
                ip_address="127.0.0.1",
                user_agent="Test Script"
            )
            
            print(f"\n🧪 License Validation Result:")
            print(f"   Valid: {result.valid}")
            print(f"   Expires At: {result.expires_at}")
            print(f"   End Time: {result.end_time}")
            print(f"   Days Until Expiry: {result.days_until_expiry}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

def clear_subscription_end_time():
    """Example of clearing the end_time field (falling back to current_period_end)."""
    
    print("\n🔄 CLEARING SUBSCRIPTION END TIME EXAMPLE")
    print("=" * 60)
    
    db = next(get_db())
    
    try:
        # Find subscriptions with end_time set
        subscription = db.query(Subscription).filter(
            Subscription.end_time.isnot(None)
        ).first()
        
        if not subscription:
            print("❌ No subscriptions with end_time set found")
            return
        
        user = subscription.user
        
        print(f"📋 Before Clearing:")
        print(f"   User: {user.email}")
        print(f"   Current Period End: {subscription.current_period_end}")
        print(f"   End Time: {subscription.end_time}")
        
        # Clear the end_time
        subscription.end_time = None
        
        db.commit()
        db.refresh(subscription)
        
        print(f"\n✅ After Clearing:")
        print(f"   Current Period End: {subscription.current_period_end}")
        print(f"   End Time: {subscription.end_time or 'Not set'}")
        
        print(f"\n💡 Impact:")
        print(f"   • License validation will now fall back to current_period_end")
        print(f"   • Normal billing cycle behavior restored")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("🔧 SUBSCRIPTION END TIME MANAGEMENT")
    print("=" * 60)
    
    # Demo setting custom end time
    set_subscription_end_time()
    
    # Demo clearing end time
    clear_subscription_end_time()
    
    print("\n" + "=" * 60)
    print("✅ End time management demo completed!")
    print("\n💡 Use cases for end_time:")
    print("   • Grace periods after billing failures")
    print("   • Custom trial extensions")
    print("   • Promotional period extensions")
    print("   • Manual subscription adjustments")
