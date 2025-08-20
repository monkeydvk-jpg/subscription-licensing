#!/usr/bin/env python3
"""
Script to view subscription details including expiration times and status.
This shows where expiration is set and how to view time information.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import sqlite3
from tabulate import tabulate

# Add the app directory to the Python path
sys.path.append(str(Path(__file__).parent))

from app.database import get_db
from app.models import User, Subscription, License, SubscriptionStatus
from app.services.license_service import LicenseService

def view_subscription_details():
    """Display detailed subscription information including expiration times."""
    
    print("📊 SUBSCRIPTION EXPIRATION DETAILS")
    print("=" * 80)
    
    db = next(get_db())
    
    try:
        # Get all subscriptions with user information
        subscriptions = db.query(Subscription).join(User).all()
        
        if not subscriptions:
            print("❌ No subscriptions found in database")
            return
        
        print(f"Found {len(subscriptions)} subscription(s)\n")
        
        # Prepare data for display
        subscription_data = []
        
        for sub in subscriptions:
            user = sub.user
            
            # Calculate days until expiry
            days_until_expiry = "N/A"
            if sub.current_period_end:
                days_diff = (sub.current_period_end - datetime.utcnow()).days
                days_until_expiry = f"{days_diff} days"
                if days_diff < 0:
                    days_until_expiry = f"EXPIRED {abs(days_diff)} days ago"
                elif days_diff == 0:
                    days_until_expiry = "EXPIRES TODAY"
            
            # Format dates
            start_date = sub.current_period_start.strftime("%Y-%m-%d %H:%M") if sub.current_period_start else "N/A"
            end_date = sub.current_period_end.strftime("%Y-%m-%d %H:%M") if sub.current_period_end else "N/A"
            end_time = sub.end_time.strftime("%Y-%m-%d %H:%M") if sub.end_time else "N/A"
            trial_end = sub.trial_end.strftime("%Y-%m-%d %H:%M") if sub.trial_end else "N/A"
            
            # Status with emoji
            status_emoji = {
                'active': '🟢',
                'trialing': '🟡',
                'past_due': '🟠',
                'canceled': '🔴',
                'ended': '⚫',
                'unpaid': '❌'
            }
            
            status_display = f"{status_emoji.get(sub.status.value, '❓')} {sub.status.value.upper()}"
            
            subscription_data.append([
                sub.id,
                user.email[:20] + "..." if len(user.email) > 20 else user.email,
                sub.plan_name or "Unknown",
                sub.billing_cycle or "N/A",
                status_display,
                start_date,
                end_date,
                end_time,
                days_until_expiry,
                trial_end,
                "YES" if sub.cancel_at_period_end else "NO"
            ])
        
        # Display table
        headers = [
            "ID", "User Email", "Plan", "Billing", "Status", 
            "Period Start", "Period End", "End Time", "Days Until Expiry", 
            "Trial End", "Will Cancel"
        ]
        
        print(tabulate(subscription_data, headers=headers, tablefmt="grid"))
        
        print("\n📍 EXPIRATION LOGIC EXPLANATION:")
        print("-" * 50)
        print("• EXPIRES AT: subscription.current_period_end")
        print("• DAYS CALCULATION: (current_period_end - now).days")  
        print("• NEXT RENEWAL: current_period_end (if not canceled)")
        print("• TRIAL EXPIRY: trial_end field (for trial subscriptions)")
        
    except Exception as e:
        print(f"❌ Error viewing subscription details: {e}")
    finally:
        db.close()

def view_license_expiration():
    """Show license expiration information."""
    
    print("\n🔑 LICENSE EXPIRATION DETAILS")
    print("=" * 80)
    
    db = next(get_db())
    
    try:
        licenses = db.query(License).join(User).all()
        
        if not licenses:
            print("❌ No licenses found in database")
            return
        
        license_data = []
        
        for license in licenses:
            user = license.user
            
            # Get subscription for this user
            subscription = db.query(Subscription).filter(
                Subscription.user_id == user.id
            ).order_by(Subscription.created_at.desc()).first()
            
            # Format dates
            created = license.created_at.strftime("%Y-%m-%d %H:%M")
            last_validated = license.last_validated.strftime("%Y-%m-%d %H:%M") if license.last_validated else "Never"
            expires = license.expires_at.strftime("%Y-%m-%d %H:%M") if license.expires_at else "No expiry"
            
            # License status
            if not license.is_active:
                status = "🔴 INACTIVE"
            elif license.is_suspended:
                status = "⏸️ SUSPENDED"
            else:
                status = "🟢 ACTIVE"
            
            # Days until license expires
            license_days = "N/A"
            if license.expires_at:
                days_diff = (license.expires_at - datetime.utcnow()).days
                if days_diff < 0:
                    license_days = f"EXPIRED {abs(days_diff)} days ago"
                else:
                    license_days = f"{days_diff} days"
            
            license_data.append([
                license.id,
                user.email[:20] + "..." if len(user.email) > 20 else user.email,
                license.license_key[:12] + "...",
                status,
                created,
                last_validated,
                expires,
                license_days,
                license.validation_count,
                subscription.status.value.upper() if subscription else "NO SUB"
            ])
        
        headers = [
            "ID", "User", "License Key", "Status", "Created", 
            "Last Validated", "Expires At", "Days Left", "Validations", "Sub Status"
        ]
        
        print(tabulate(license_data, headers=headers, tablefmt="grid"))
        
        print("\n📍 LICENSE EXPIRATION LOGIC:")
        print("-" * 50)
        print("• LICENSE EXPIRES AT: license.expires_at")
        print("• USUALLY SET TO: subscription.current_period_end")
        print("• VALIDATION UPDATES: license.last_validated = now()")
        print("• STATUS CHECK: Based on subscription.status")
        
    except Exception as e:
        print(f"❌ Error viewing license details: {e}")
    finally:
        db.close()

def test_license_validation():
    """Test license validation to see expiration in action."""
    
    print("\n🧪 LICENSE VALIDATION TEST")
    print("=" * 80)
    
    db = next(get_db())
    
    try:
        # Get first active license for testing
        license = db.query(License).filter(License.is_active == True).first()
        
        if not license:
            print("❌ No active licenses found for testing")
            return
        
        print(f"Testing license: {license.license_key[:12]}...")
        
        # Create license service and validate
        license_service = LicenseService(db)
        
        result = license_service.validate_license(
            license.license_key,
            ip_address="127.0.0.1",
            user_agent="Test Script"
        )
        
        print(f"\n📊 VALIDATION RESULT:")
        print(f"Valid: {result.valid}")
        print(f"Message: {result.message}")
        print(f"Error Code: {result.error_code}")
        
        if result.valid:
            print(f"\n⏰ EXPIRATION INFORMATION:")
            print(f"Expires At: {result.expires_at}")
            print(f"Days Until Expiry: {result.days_until_expiry}")
            print(f"Current Period End: {result.current_period_end}")
            print(f"Next Renewal: {result.next_renewal_date}")
            print(f"Will Cancel: {result.cancel_at_period_end}")
            print(f"Plan: {result.subscription_plan}")
            print(f"Status: {result.subscription_status}")
        
    except Exception as e:
        print(f"❌ Error testing license validation: {e}")
    finally:
        db.close()

def show_expiration_sources():
    """Show where expiration dates come from."""
    
    print("\n🎯 EXPIRATION DATE SOURCES")
    print("=" * 80)
    
    print("""
📅 SUBSCRIPTION EXPIRATION:
   ├── current_period_start    ← When current billing period started
   ├── current_period_end      ← When current billing period ends (MAIN EXPIRY)
   ├── end_time               ← Explicit subscription end time (overrides period_end if set)
   ├── trial_end              ← When trial period ends (if applicable)
   └── cancel_at_period_end   ← Whether subscription will auto-cancel

🔑 LICENSE EXPIRATION:
   ├── expires_at             ← Usually set to subscription.current_period_end
   ├── last_validated         ← Last time license was checked
   └── is_active/is_suspended ← Manual activation controls

⚙️  CALCULATION LOGIC:
   ├── Days Until Expiry = (current_period_end - now()).days
   ├── Next Renewal = current_period_end (if not canceling)
   ├── Status Colors:
   │   ├── 🟢 Green: 30+ days remaining
   │   ├── 🟡 Yellow: 7-30 days remaining
   │   └── 🔴 Red: <7 days or expired
   └── Validation: Checks subscription.status for active/trialing

📍 KEY FILES:
   ├── models.py              ← Database schema definitions
   ├── license_service.py     ← Expiration calculation logic
   ├── populate_sample_data.py ← Where sample expiry dates are set
   └── Extension UI           ← Where expiry info is displayed

🔄 UPDATE TRIGGERS:
   ├── Stripe Webhooks        ← Real subscription updates
   ├── Manual Admin Changes  ← Direct database updates
   ├── License Validation    ← Periodic checks every 10 minutes
   └── Extension Startup     ← Browser restart validation
""")

if __name__ == "__main__":
    print("🔍 SUBSCRIPTION & LICENSE EXPIRATION VIEWER")
    print("=" * 80)
    
    # Show expiration sources first
    show_expiration_sources()
    
    # View subscription details
    view_subscription_details()
    
    # View license expiration
    view_license_expiration()
    
    # Test license validation
    test_license_validation()
    
    print("\n" + "=" * 80)
    print("✅ Expiration details viewing completed!")
    print("\n💡 To modify expiration dates:")
    print("   • Update subscription.current_period_end in database")
    print("   • Restart extension to see changes in UI")
    print("   • Use admin dashboard for manual adjustments")
