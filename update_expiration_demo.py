#!/usr/bin/env python3
"""
Script to update license expiration dates for demonstration.
This shows how to set and modify subscription expiration times.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add the app directory to the Python path
sys.path.append(str(Path(__file__).parent))

from app.database import get_db
from app.models import User, Subscription, License, SubscriptionStatus

def update_license_expiration_demo():
    """Update some licenses with proper expiration dates for demonstration."""
    
    print("🔧 UPDATING LICENSE EXPIRATION DATES")
    print("=" * 60)
    
    db = next(get_db())
    
    try:
        # Get first few active licenses
        active_licenses = db.query(License).filter(License.is_active == True).limit(3).all()
        
        if not active_licenses:
            print("❌ No active licenses found to update")
            return
        
        now = datetime.utcnow()
        
        # Update each license with different expiration scenarios
        scenarios = [
            {"days": 5, "desc": "Expiring soon (5 days)"},
            {"days": 25, "desc": "Normal expiration (25 days)"},
            {"days": -3, "desc": "Already expired (3 days ago)"}
        ]
        
        for i, license in enumerate(active_licenses):
            scenario = scenarios[i % len(scenarios)]
            
            # Calculate expiration date
            expires_at = now + timedelta(days=scenario["days"])
            
            # Update license
            license.expires_at = expires_at
            
            # Also update the corresponding subscription
            subscription = db.query(Subscription).filter(
                Subscription.user_id == license.user_id
            ).first()
            
            if subscription:
                # Set subscription period to match license expiry
                subscription.current_period_start = now - timedelta(days=15)
                subscription.current_period_end = expires_at
                
                # Set status based on expiration
                if scenario["days"] < 0:
                    subscription.status = SubscriptionStatus.ENDED
                    license.is_active = False
                elif scenario["days"] < 7:
                    subscription.status = SubscriptionStatus.PAST_DUE
                else:
                    subscription.status = SubscriptionStatus.ACTIVE
            
            print(f"✅ Updated License ID {license.id}:")
            print(f"   User: {license.user.email}")
            print(f"   License Key: {license.license_key[:12]}...")
            print(f"   Scenario: {scenario['desc']}")
            print(f"   Expires At: {expires_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            print(f"   Status: {subscription.status.value if subscription else 'No subscription'}")
            print()
        
        # Commit changes
        db.commit()
        print("🎉 License expiration dates updated successfully!")
        
    except Exception as e:
        print(f"❌ Error updating expiration dates: {e}")
        db.rollback()
    finally:
        db.close()

def show_expiration_examples():
    """Show examples of how expiration dates are calculated and used."""
    
    print("\n📚 EXPIRATION DATE EXAMPLES")
    print("=" * 60)
    
    now = datetime.utcnow()
    
    examples = [
        {
            "name": "Monthly Subscription",
            "start": now - timedelta(days=10),
            "end": now + timedelta(days=20),
            "billing": "monthly"
        },
        {
            "name": "Yearly Subscription", 
            "start": now - timedelta(days=100),
            "end": now + timedelta(days=265),
            "billing": "yearly"
        },
        {
            "name": "Trial Subscription",
            "start": now - timedelta(days=3),
            "end": now + timedelta(days=11),
            "billing": "trial"
        },
        {
            "name": "Expired Subscription",
            "start": now - timedelta(days=40),
            "end": now - timedelta(days=10),
            "billing": "monthly"
        }
    ]
    
    for example in examples:
        days_left = (example["end"] - now).days
        
        print(f"📋 {example['name']} ({example['billing']}):")
        print(f"   Period Start: {example['start'].strftime('%Y-%m-%d %H:%M')}")
        print(f"   Period End:   {example['end'].strftime('%Y-%m-%d %H:%M')}")
        print(f"   Days Left:    {days_left} days")
        
        if days_left < 0:
            print(f"   Status:       🔴 EXPIRED ({abs(days_left)} days ago)")
        elif days_left < 7:
            print(f"   Status:       🟡 EXPIRING SOON")
        else:
            print(f"   Status:       🟢 ACTIVE")
        print()

def demonstrate_time_calculations():
    """Demonstrate how time calculations work in the system."""
    
    print("\n⏰ TIME CALCULATION DEMONSTRATIONS")
    print("=" * 60)
    
    now = datetime.utcnow()
    print(f"Current Time (UTC): {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Show different time scenarios
    scenarios = [
        {"name": "30 days from now", "delta": timedelta(days=30)},
        {"name": "7 days from now", "delta": timedelta(days=7)},
        {"name": "1 day from now", "delta": timedelta(days=1)},
        {"name": "12 hours from now", "delta": timedelta(hours=12)},
        {"name": "3 days ago", "delta": timedelta(days=-3)},
        {"name": "1 month ago", "delta": timedelta(days=-30)}
    ]
    
    print("📊 Expiration Time Scenarios:")
    print("-" * 40)
    
    for scenario in scenarios:
        future_time = now + scenario["delta"]
        days_diff = scenario["delta"].days
        
        print(f"{scenario['name']:20} | {future_time.strftime('%Y-%m-%d %H:%M')} | {days_diff:3d} days")
    
    print("\n🎯 Key Points:")
    print("• All times are stored in UTC")
    print("• Days calculation: (expiry_date - current_date).days")
    print("• Negative days = expired")
    print("• Extension shows user's local timezone")
    print("• Server validation uses UTC consistently")

def show_where_expiry_is_set():
    """Show where expiration dates are set in the codebase."""
    
    print("\n📍 WHERE EXPIRATION IS SET")
    print("=" * 60)
    
    print("""
🏗️  DATABASE SCHEMA (models.py):
   └── Subscription table:
       ├── current_period_start  (DATETIME)
       ├── current_period_end    (DATETIME) ← PRIMARY EXPIRY FIELD
       └── trial_end            (DATETIME)
   
   └── License table:
       ├── expires_at           (DATETIME) ← USUALLY SAME AS SUBSCRIPTION
       └── last_validated       (DATETIME)

⚙️  LICENSE SERVICE (license_service.py):
   └── validate_license():
       ├── Line 119: days_until_expiry = (subscription.current_period_end - datetime.utcnow()).days
       ├── Line 122: next_renewal_date = subscription.current_period_end
       └── Line 133: expires_at=subscription.current_period_end

🎮 EXTENSION (background.js):
   └── validateLicense():
       ├── Receives expiration data from API
       ├── Stores in: this.subscriptionInfo.expires_at
       └── Updates UI with formatted dates

🖼️  UI DISPLAY (sidebar.js):
   └── updateSubscriptionDisplay():
       ├── Line 335: new Date(subscriptionInfo.current_period_end)
       ├── Line 336: expiryDate.toLocaleDateString()
       └── Color coding based on days_until_expiry

📅 SAMPLE DATA (populate_sample_data.py):
   └── create_sample_data():
       ├── Line 67: period_end = now + timedelta(days=15)
       ├── Line 77: expires_at=period_end
       └── Different scenarios for testing
""")

if __name__ == "__main__":
    print("⏰ SUBSCRIPTION EXPIRATION TIME DEMO")
    print("=" * 60)
    
    # Show where expiry is set
    show_where_expiry_is_set()
    
    # Show calculation examples
    demonstrate_time_calculations()
    
    # Show practical examples
    show_expiration_examples()
    
    # Update some real data for testing
    print("\n🔧 UPDATING DEMO DATA...")
    update_license_expiration_demo()
    
    print("\n" + "=" * 60)
    print("✅ Expiration demonstration completed!")
    print("\n💡 Key Takeaways:")
    print("   • Expiration = subscription.current_period_end")
    print("   • Days left = (expiry_date - now).days")
    print("   • All dates stored in UTC")
    print("   • UI shows user's local timezone")
    print("   • Colors: 🟢 30+ days, 🟡 7-30 days, 🔴 <7 days")
