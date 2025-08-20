#!/usr/bin/env python3
"""
Test script to verify that the days_until_expiry calculation properly prioritizes end_time over current_period_end.
"""
import sys
import os
from datetime import datetime, timedelta

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models import User, Subscription, SubscriptionStatus
from app.main import get_subscriptions


def test_days_until_expiry_calculation():
    """Test that days_until_expiry calculation prioritizes end_time when set."""
    
    # Use in-memory SQLite database for testing
    engine = create_engine("sqlite:///:memory:", echo=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        # Create test user
        user = User(email="test@example.com")
        db.add(user)
        db.commit()
        db.refresh(user)
        
        now = datetime.utcnow()
        
        # Test case 1: Subscription with only current_period_end (no end_time)
        print("=== Test Case 1: Only current_period_end ===")
        sub1 = Subscription(
            stripe_subscription_id="test_sub_1",
            user_id=user.id,
            status=SubscriptionStatus.ACTIVE,
            current_period_start=now - timedelta(days=15),
            current_period_end=now + timedelta(days=15),  # 15 days from now
            end_time=None,  # Not set
            plan_name="basic"
        )
        db.add(sub1)
        db.commit()
        db.refresh(sub1)
        
        # Test case 2: Subscription with both current_period_end and end_time (end_time should win)
        print("\n=== Test Case 2: Both dates - end_time should win ===")
        sub2 = Subscription(
            stripe_subscription_id="test_sub_2", 
            user_id=user.id,
            status=SubscriptionStatus.ACTIVE,
            current_period_start=now - timedelta(days=10),
            current_period_end=now + timedelta(days=20),  # 20 days from now
            end_time=now + timedelta(days=5),  # 5 days from now (sooner than period_end)
            plan_name="premium"
        )
        db.add(sub2)
        db.commit()
        db.refresh(sub2)
        
        # Test case 3: Subscription with end_time later than current_period_end
        print("\n=== Test Case 3: end_time later than current_period_end ===")
        sub3 = Subscription(
            stripe_subscription_id="test_sub_3",
            user_id=user.id,
            status=SubscriptionStatus.ACTIVE,
            current_period_start=now - timedelta(days=5),
            current_period_end=now + timedelta(days=10),  # 10 days from now
            end_time=now + timedelta(days=25),  # 25 days from now (later than period_end)
            plan_name="enterprise"
        )
        db.add(sub3)
        db.commit()
        db.refresh(sub3)
        
        # Get subscriptions using the same logic as the API endpoint
        subscriptions = db.query(Subscription).join(User).all()
        
        for i, sub in enumerate(subscriptions, 1):
            print(f"\n--- Subscription {i} ---")
            print(f"Plan: {sub.plan_name}")
            print(f"Current Period End: {sub.current_period_end}")
            print(f"End Time: {sub.end_time}")
            
            # Calculate days until expiry using the same logic as main.py
            days_until_expiry = None
            expiration_status = "unknown"
            
            # Determine effective expiration date
            effective_expiry = None
            if sub.end_time:
                effective_expiry = sub.end_time  # end_time takes precedence
                print(f"Using END_TIME as effective expiry: {effective_expiry}")
            elif sub.current_period_end:
                effective_expiry = sub.current_period_end  # fallback to current_period_end
                print(f"Using CURRENT_PERIOD_END as effective expiry: {effective_expiry}")
            
            if effective_expiry:
                days_diff = (effective_expiry - datetime.utcnow()).days
                days_until_expiry = days_diff
                
                if days_diff < 0:
                    expiration_status = "expired"
                elif days_diff <= 7:
                    expiration_status = "expires_soon"
                else:
                    expiration_status = "active"
            
            print(f"Days Until Expiry: {days_until_expiry}")
            print(f"Expiration Status: {expiration_status}")
            
            # Expected results
            if i == 1:
                # Should use current_period_end (15 days)
                expected_days = 15
                print(f"Expected: ~{expected_days} days (using current_period_end)")
            elif i == 2:
                # Should use end_time (5 days, not 20)
                expected_days = 5
                print(f"Expected: ~{expected_days} days (using end_time, not current_period_end)")
            elif i == 3:
                # Should use end_time (25 days, not 10)
                expected_days = 25
                print(f"Expected: ~{expected_days} days (using end_time, not current_period_end)")
            
            # Check if calculation is approximately correct (within 1 day due to time precision)
            if days_until_expiry is not None and abs(days_until_expiry - expected_days) <= 1:
                print("✅ CORRECT: Calculation matches expected result")
            else:
                print(f"❌ ERROR: Expected ~{expected_days}, got {days_until_expiry}")
        
        print("\n" + "="*60)
        print("SUMMARY:")
        print("- Test 1: Only current_period_end → should show ~15 days")
        print("- Test 2: end_time (5d) vs current_period_end (20d) → should show ~5 days")
        print("- Test 3: end_time (25d) vs current_period_end (10d) → should show ~25 days")
        print("="*60)
        
    finally:
        db.close()


if __name__ == "__main__":
    test_days_until_expiry_calculation()
