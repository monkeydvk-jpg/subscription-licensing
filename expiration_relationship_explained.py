#!/usr/bin/env python3
"""
SUBSCRIPTION vs LICENSE EXPIRATION RELATIONSHIP EXPLAINED

This script demonstrates and explains how subscription and license expiration
are related in your licensing system.
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

def show_expiration_relationship():
    """Explain the relationship between subscription and license expiration."""
    
    print("SUBSCRIPTION vs LICENSE EXPIRATION RELATIONSHIP")
    print("=" * 80)
    
    print("""
KEY CONCEPT: LICENSES DON'T EXPIRE DIRECTLY - SUBSCRIPTIONS DO!

┌─────────────────┐    Controls    ┌─────────────────┐
│   SUBSCRIPTION  │ ──────────────→ │     LICENSE     │
│                 │    Expiration   │                 │
│ • current_period_end ──────────→ │ • expires_at    │
│ • status        │               │ • is_active     │
│ • cancel_at...  │               │ • is_suspended  │
└─────────────────┘               └─────────────────┘

HOW IT WORKS:
1. SUBSCRIPTION determines the expiration timeline
2. LICENSE inherits expiration behavior from subscription
3. License validation ALWAYS checks subscription status first
4. License can be manually suspended/activated independently

EXPIRATION HIERARCHY:
├── PRIMARY: Subscription.current_period_end (MAIN EXPIRY DATE)
├── SECONDARY: Subscription.status (active, trialing, past_due, etc.)
├── OVERRIDE: License.is_active (manual on/off switch)
└── OVERRIDE: License.is_suspended (manual suspension)
""")

def analyze_current_data():
    """Analyze current database to show relationship in action."""
    
    print("\nCURRENT DATA ANALYSIS")
    print("=" * 80)
    
    db = next(get_db())
    
    try:
        # Get users with both subscriptions and licenses
        users = db.query(User).all()
        analysis_data = []
        
        for user in users:
            subscriptions = db.query(Subscription).filter(Subscription.user_id == user.id).all()
            licenses = db.query(License).filter(License.user_id == user.id).all()
            
            if subscriptions and licenses:
                # Get latest subscription
                latest_sub = max(subscriptions, key=lambda s: s.created_at)
                
                for license in licenses:
                    # Compare subscription vs license expiration
                    sub_expires = latest_sub.current_period_end.strftime("%Y-%m-%d %H:%M") if latest_sub.current_period_end else "N/A"
                    license_expires = license.expires_at.strftime("%Y-%m-%d %H:%M") if license.expires_at else "No expiry"
                    
                    # Determine who controls expiration
                    expiry_controller = "SUBSCRIPTION"
                    if license.expires_at and latest_sub.current_period_end:
                        if license.expires_at != latest_sub.current_period_end:
                            expiry_controller = "LICENSE (Override)"
                    elif license.expires_at and not latest_sub.current_period_end:
                        expiry_controller = "LICENSE (Independent)"
                    elif not license.expires_at:
                        expiry_controller = "SUBSCRIPTION"
                    
                    analysis_data.append([
                        user.email[:20] + "..." if len(user.email) > 20 else user.email,
                        latest_sub.status.value.upper(),
                        sub_expires,
                        "[ACTIVE]" if license.is_active else "[INACTIVE]",
                        "[SUSPENDED]" if license.is_suspended else "[OK]",
                        license_expires,
                        expiry_controller
                    ])
        
        headers = [
            "User", "Sub Status", "Sub Expires", "License Active", 
            "License Status", "License Expires", "Expiry Controlled By"
        ]
        
        print(tabulate(analysis_data, headers=headers, tablefmt="grid"))
        
    except Exception as e:
        print(f"Error analyzing data: {e}")
    finally:
        db.close()

def show_validation_flow():
    """Show how validation works with both subscription and license."""
    
    print("\nLICENSE VALIDATION FLOW")
    print("=" * 80)
    
    print("""
VALIDATION PRIORITY ORDER:

1. CHECK LICENSE TABLE:
   ├── license.is_active == False?  → FAIL: "License key is inactive"
   └── license.is_suspended == True? → FAIL: "License key is suspended"

2. CHECK SUBSCRIPTION TABLE:
   ├── No subscription found?        → FAIL: "No active subscription found"
   ├── subscription.status not in [active, trialing]? → FAIL: "Subscription is [status]"
   └── subscription.current_period_end < now()? → Check status logic

3. CALCULATE EXPIRATION:
   ├── expires_at = subscription.current_period_end
   ├── days_until_expiry = (current_period_end - now()).days
   └── next_renewal_date = current_period_end (if not canceling)

4. RETURN SUCCESS with subscription-based expiration info

KEY POINT: Even if license.expires_at is set differently,
the validation ALWAYS uses subscription.current_period_end for expiration!
""")

def demonstrate_expiration_sources():
    """Show practical examples of expiration sources."""
    
    print("\nEXPIRATION SOURCES IN PRACTICE")
    print("=" * 80)
    
    db = next(get_db())
    
    try:
        # Get a few example records
        examples = []
        
        # Find an active subscription with license
        active_sub = db.query(Subscription).filter(
            Subscription.status == SubscriptionStatus.ACTIVE
        ).first()
        
        if active_sub:
            user = active_sub.user
            license = db.query(License).filter(License.user_id == user.id).first()
            
            if license:
                examples.append({
                    "scenario": "NORMAL CASE",
                    "description": "License follows subscription expiration",
                    "subscription_expires": active_sub.current_period_end.strftime("%Y-%m-%d %H:%M") if active_sub.current_period_end else "N/A",
                    "license_expires": license.expires_at.strftime("%Y-%m-%d %H:%M") if license.expires_at else "No expiry",
                    "validation_uses": "subscription.current_period_end",
                    "who_controls": "SUBSCRIPTION"
                })
        
        # Find a suspended license
        suspended_license = db.query(License).filter(License.is_suspended == True).first()
        if suspended_license:
            user = suspended_license.user
            subscription = db.query(Subscription).filter(Subscription.user_id == user.id).first()
            
            examples.append({
                "scenario": "SUSPENDED LICENSE",
                "description": "License manually suspended, ignores subscription",
                "subscription_expires": subscription.current_period_end.strftime("%Y-%m-%d %H:%M") if subscription and subscription.current_period_end else "N/A",
                "license_expires": "SUSPENDED (overrides expiry)",
                "validation_uses": "license.is_suspended check (fails immediately)",
                "who_controls": "LICENSE (override)"
            })
        
        # Display examples
        for i, example in enumerate(examples, 1):
            print(f"\nEXAMPLE {i}: {example['scenario']}")
            print("-" * 40)
            print(f"Description: {example['description']}")
            print(f"Subscription Expires: {example['subscription_expires']}")
            print(f"License Expires: {example['license_expires']}")
            print(f"Validation Uses: {example['validation_uses']}")
            print(f"Controlled By: {example['who_controls']}")
        
    except Exception as e:
        print(f"Error demonstrating examples: {e}")
    finally:
        db.close()

def show_code_evidence():
    """Show the actual code that proves the relationship."""
    
    print("\nCODE EVIDENCE")
    print("=" * 80)
    
    print("""
FROM license_service.py - validate_license() method:

Line 133: expires_at=subscription.current_period_end,
Line 119: days_until_expiry = (subscription.current_period_end - datetime.utcnow()).days

This PROVES that license expiration is ALWAYS based on subscription!

VALIDATION LOGIC ORDER:
1. Check license.is_active and license.is_suspended (Lines 70-85)
2. Get subscription for the user (Line 88)
3. Check subscription.status (Line 98)
4. Use subscription.current_period_end for all expiry calculations (Lines 118-123)
5. Return subscription-based expiration data (Lines 129-141)

CONCLUSION: 
- License table CAN have expires_at field
- But validation IGNORES license.expires_at 
- Validation ALWAYS uses subscription.current_period_end
- License fields (is_active, is_suspended) can OVERRIDE and block access
- But expiration timing comes from SUBSCRIPTION only
""")

def create_summary_table():
    """Create a summary table of what controls what."""
    
    print("\nCONTROL SUMMARY TABLE")
    print("=" * 80)
    
    control_data = [
        ["Expiration Date", "subscription.current_period_end", "Always used in validation"],
        ["Days Until Expiry", "subscription.current_period_end", "Calculated from subscription"],
        ["Next Renewal", "subscription.current_period_end", "Unless cancel_at_period_end=True"],
        ["Access Permission", "license.is_active", "Can block access regardless of subscription"],
        ["Suspension Status", "license.is_suspended", "Can block access regardless of subscription"],
        ["Plan Information", "subscription.plan_name", "Displayed to user"],
        ["Billing Cycle", "subscription.billing_cycle", "Displayed to user"],
        ["Trial End", "subscription.trial_end", "For trial subscriptions"],
        ["Subscription Status", "subscription.status", "Must be active/trialing for access"]
    ]
    
    headers = ["What It Controls", "Source Field", "Notes"]
    print(tabulate(control_data, headers=headers, tablefmt="grid"))

if __name__ == "__main__":
    show_expiration_relationship()
    analyze_current_data()
    show_validation_flow()
    demonstrate_expiration_sources()
    show_code_evidence()
    create_summary_table()
    
    print("\n" + "=" * 80)
    print("FINAL ANSWER:")
    print("EXPIRATION IS BASED ON SUBSCRIPTION, NOT LICENSE!")
    print("License can override access (suspend/deactivate) but not expiration timing.")
    print("=" * 80)
