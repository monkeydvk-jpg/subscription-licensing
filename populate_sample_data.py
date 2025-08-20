#!/usr/bin/env python3
"""
Script to populate sample subscription data for testing.
This creates sample users, subscriptions, and licenses with the new plan information.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import sqlite3

# Add the app directory to the Python path
sys.path.append(str(Path(__file__).parent))

from app.database import get_db
from app.models import User, Subscription, License, SubscriptionStatus
from app.security import generate_license_key, hash_license_key

def create_sample_data():
    """Create sample data for testing."""
    
    print("🚀 Creating sample subscription data...")
    
    # Get database connection
    db = next(get_db())
    
    try:
        # Check if we already have sample data
        existing_user = db.query(User).filter(User.email == "test@example.com").first()
        if existing_user:
            print("Sample data already exists. Updating existing records...")
            update_existing_data(db)
            return
        
        # Create sample users
        users_data = [
            {
                "email": "test@example.com", 
                "stripe_customer_id": "cus_test_123",
                "plan_name": "Pro Plan",
                "billing_cycle": "monthly",
                "status": SubscriptionStatus.ACTIVE
            },
            {
                "email": "trial@example.com", 
                "stripe_customer_id": "cus_test_456",
                "plan_name": "Basic Plan",
                "billing_cycle": "yearly",
                "status": SubscriptionStatus.TRIALING
            },
            {
                "email": "expired@example.com", 
                "stripe_customer_id": "cus_test_789",
                "plan_name": "Premium Plan",
                "billing_cycle": "monthly",
                "status": SubscriptionStatus.ENDED
            }
        ]
        
        for user_data in users_data:
            # Create user
            user = User(
                email=user_data["email"],
                stripe_customer_id=user_data["stripe_customer_id"]
            )
            db.add(user)
            db.flush()  # Get the user ID
            
            # Create subscription
            now = datetime.utcnow()
            if user_data["status"] == SubscriptionStatus.ACTIVE:
                period_start = now - timedelta(days=15)
                period_end = now + timedelta(days=15)
                trial_end = None
            elif user_data["status"] == SubscriptionStatus.TRIALING:
                period_start = now - timedelta(days=3)
                period_end = now + timedelta(days=11)  # 14-day trial
                trial_end = period_end
            else:  # ENDED
                period_start = now - timedelta(days=35)
                period_end = now - timedelta(days=5)
                trial_end = None
            
            subscription = Subscription(
                stripe_subscription_id=f"sub_test_{user.id}",
                user_id=user.id,
                status=user_data["status"],
                current_period_start=period_start,
                current_period_end=period_end,
                cancel_at_period_end=False,
                stripe_price_id=f"price_test_{user_data['billing_cycle']}",
                plan_name=user_data["plan_name"],
                billing_cycle=user_data["billing_cycle"],
                trial_end=trial_end
            )
            db.add(subscription)
            
            # Create license
            license_key = generate_license_key()
            license_key_hash = hash_license_key(license_key)
            
            license = License(
                license_key=license_key,
                license_key_hash=license_key_hash,
                user_id=user.id,
                is_active=user_data["status"] in [SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING],
                is_suspended=False,
                expires_at=period_end,
                extension_version="2.0",
                validation_count=0
            )
            db.add(license)
            
            print(f"✅ Created user: {user_data['email']}")
            print(f"   License Key: {license_key}")
            print(f"   Plan: {user_data['plan_name']} ({user_data['billing_cycle']})")
            print(f"   Status: {user_data['status'].value}")
            print(f"   Period: {period_start.strftime('%Y-%m-%d')} to {period_end.strftime('%Y-%m-%d')}")
            print()
        
        # Commit all changes
        db.commit()
        print("🎉 Sample data created successfully!")
        
    except Exception as e:
        print(f"❌ Error creating sample data: {e}")
        db.rollback()
        raise
    finally:
        db.close()

def update_existing_data(db):
    """Update existing data with new subscription plan information."""
    
    print("🔄 Updating existing subscriptions with plan information...")
    
    try:
        subscriptions = db.query(Subscription).all()
        
        plans = [
            {"name": "Pro Plan", "cycle": "monthly", "price_id": "price_test_monthly"},
            {"name": "Basic Plan", "cycle": "yearly", "price_id": "price_test_yearly"},
            {"name": "Premium Plan", "cycle": "monthly", "price_id": "price_test_premium"}
        ]
        
        for i, subscription in enumerate(subscriptions):
            plan = plans[i % len(plans)]  # Cycle through plans
            
            subscription.plan_name = plan["name"]
            subscription.billing_cycle = plan["cycle"]
            subscription.stripe_price_id = plan["price_id"]
            
            # Set trial_end for trialing subscriptions
            if subscription.status == SubscriptionStatus.TRIALING:
                subscription.trial_end = subscription.current_period_end
            
            print(f"✅ Updated subscription {subscription.id}: {plan['name']} ({plan['cycle']})")
        
        db.commit()
        print("🎉 Existing data updated successfully!")
        
    except Exception as e:
        print(f"❌ Error updating existing data: {e}")
        db.rollback()
        raise

def verify_sample_data():
    """Verify that the sample data was created correctly."""
    
    print("🔍 Verifying sample data...")
    
    db = next(get_db())
    
    try:
        users = db.query(User).all()
        print(f"Users created: {len(users)}")
        
        subscriptions = db.query(Subscription).all()
        print(f"Subscriptions created: {len(subscriptions)}")
        
        licenses = db.query(License).all()
        print(f"Licenses created: {len(licenses)}")
        
        # Show details for one subscription
        if subscriptions:
            sub = subscriptions[0]
            print(f"\nSample subscription details:")
            print(f"  Plan: {sub.plan_name}")
            print(f"  Billing Cycle: {sub.billing_cycle}")
            print(f"  Status: {sub.status.value}")
            print(f"  Stripe Price ID: {sub.stripe_price_id}")
            print(f"  Current Period: {sub.current_period_start} to {sub.current_period_end}")
            if sub.trial_end:
                print(f"  Trial End: {sub.trial_end}")
        
        print("✅ Sample data verification completed!")
        
    except Exception as e:
        print(f"❌ Error verifying sample data: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    print("🚀 Populating sample subscription data...")
    print("=" * 50)
    
    create_sample_data()
    
    print("=" * 50)
    verify_sample_data()
    
    print("=" * 50)
    print("🎉 Sample data setup completed!")
    print("\nYou can now test the license validation with the generated license keys.")
    print("The extension will show detailed subscription information for valid licenses.")
