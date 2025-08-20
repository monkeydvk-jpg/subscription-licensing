"""
Background tasks for cleanup and maintenance.
"""
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from .database import SessionLocal
from .models import ApiLog, License, Subscription, SubscriptionStatus
from .services.stripe_service import StripeService

logger = logging.getLogger(__name__)


def cleanup_old_api_logs(days_to_keep: int = 30):
    """Remove API logs older than specified days."""
    db = SessionLocal()
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        deleted_count = db.query(ApiLog).filter(
            ApiLog.timestamp < cutoff_date
        ).delete()
        
        db.commit()
        logger.info(f"Cleaned up {deleted_count} old API log entries")
        
    except Exception as e:
        logger.error(f"Error cleaning up API logs: {str(e)}")
        db.rollback()
    finally:
        db.close()


def sync_subscription_statuses():
    """Sync subscription statuses with Stripe."""
    db = SessionLocal()
    try:
        stripe_service = StripeService(db)
        
        # Get all active subscriptions
        subscriptions = db.query(Subscription).filter(
            Subscription.status.in_([
                SubscriptionStatus.ACTIVE,
                SubscriptionStatus.TRIALING,
                SubscriptionStatus.PAST_DUE
            ])
        ).all()
        
        updated_count = 0
        
        for subscription in subscriptions:
            try:
                # Get current status from Stripe
                stripe_data = stripe_service.get_subscription_details(
                    subscription.stripe_subscription_id
                )
                
                if stripe_data:
                    old_status = subscription.status
                    new_status = SubscriptionStatus(stripe_data['status'])
                    
                    if old_status != new_status:
                        subscription.status = new_status
                        subscription.current_period_start = datetime.fromtimestamp(
                            stripe_data['current_period_start']
                        )
                        subscription.current_period_end = datetime.fromtimestamp(
                            stripe_data['current_period_end']
                        )
                        subscription.cancel_at_period_end = stripe_data['cancel_at_period_end']
                        
                        updated_count += 1
                        logger.info(
                            f"Updated subscription {subscription.id} status: "
                            f"{old_status.value} -> {new_status.value}"
                        )
                        
            except Exception as e:
                logger.error(
                    f"Error syncing subscription {subscription.id}: {str(e)}"
                )
        
        db.commit()
        logger.info(f"Synced {updated_count} subscription statuses")
        
    except Exception as e:
        logger.error(f"Error syncing subscription statuses: {str(e)}")
        db.rollback()
    finally:
        db.close()


def cleanup_expired_subscriptions():
    """Suspend licenses for expired subscriptions."""
    db = SessionLocal()
    try:
        from .services.license_service import LicenseService
        
        license_service = LicenseService(db)
        
        # Find subscriptions that have ended
        expired_subscriptions = db.query(Subscription).filter(
            Subscription.status.in_([
                SubscriptionStatus.CANCELED,
                SubscriptionStatus.ENDED,
                SubscriptionStatus.UNPAID
            ]),
            Subscription.current_period_end < datetime.utcnow()
        ).all()
        
        suspended_count = 0
        
        for subscription in expired_subscriptions:
            # Get user's licenses
            licenses = license_service.get_licenses_for_user(subscription.user_id)
            
            for license in licenses:
                if license.is_active and not license.is_suspended:
                    license_service.suspend_license(license.id)
                    suspended_count += 1
                    logger.info(
                        f"Suspended license {license.id} due to expired subscription "
                        f"{subscription.id}"
                    )
        
        logger.info(f"Suspended {suspended_count} licenses for expired subscriptions")
        
    except Exception as e:
        logger.error(f"Error cleaning up expired subscriptions: {str(e)}")
        db.rollback()
    finally:
        db.close()


def update_license_expiry_dates():
    """Update license expiry dates based on subscription periods."""
    db = SessionLocal()
    try:
        # Get all active licenses with active subscriptions
        licenses = db.query(License).join(
            Subscription, License.user_id == Subscription.user_id
        ).filter(
            License.is_active == True,
            License.is_suspended == False,
            Subscription.status.in_([
                SubscriptionStatus.ACTIVE,
                SubscriptionStatus.TRIALING
            ])
        ).all()
        
        updated_count = 0
        
        for license in licenses:
            # Get the user's active subscription
            active_subscription = db.query(Subscription).filter(
                Subscription.user_id == license.user_id,
                Subscription.status.in_([
                    SubscriptionStatus.ACTIVE,
                    SubscriptionStatus.TRIALING
                ])
            ).first()
            
            if active_subscription and active_subscription.current_period_end:
                if license.expires_at != active_subscription.current_period_end:
                    license.expires_at = active_subscription.current_period_end
                    updated_count += 1
        
        db.commit()
        logger.info(f"Updated expiry dates for {updated_count} licenses")
        
    except Exception as e:
        logger.error(f"Error updating license expiry dates: {str(e)}")
        db.rollback()
    finally:
        db.close()


def generate_usage_stats():
    """Generate usage statistics for monitoring."""
    db = SessionLocal()
    try:
        # Count active licenses
        active_licenses = db.query(License).filter(
            License.is_active == True,
            License.is_suspended == False
        ).count()
        
        # Count active subscriptions
        active_subscriptions = db.query(Subscription).filter(
            Subscription.status.in_([
                SubscriptionStatus.ACTIVE,
                SubscriptionStatus.TRIALING
            ])
        ).count()
        
        # Count API calls in last 24 hours
        yesterday = datetime.utcnow() - timedelta(hours=24)
        api_calls_24h = db.query(ApiLog).filter(
            ApiLog.timestamp >= yesterday
        ).count()
        
        # Count unique users with active licenses
        from sqlalchemy import distinct
        active_users = db.query(distinct(License.user_id)).filter(
            License.is_active == True,
            License.is_suspended == False
        ).count()
        
        stats = {
            'timestamp': datetime.utcnow().isoformat(),
            'active_licenses': active_licenses,
            'active_subscriptions': active_subscriptions,
            'active_users': active_users,
            'api_calls_24h': api_calls_24h
        }
        
        logger.info(f"Usage stats: {stats}")
        
        # You could store these stats in a separate table or send to monitoring service
        
        return stats
        
    except Exception as e:
        logger.error(f"Error generating usage stats: {str(e)}")
        return None
    finally:
        db.close()


def run_all_maintenance_tasks():
    """Run all maintenance tasks."""
    logger.info("Starting maintenance tasks")
    
    try:
        cleanup_old_api_logs()
        sync_subscription_statuses()
        cleanup_expired_subscriptions()
        update_license_expiry_dates()
        generate_usage_stats()
        
        logger.info("Completed all maintenance tasks")
        
    except Exception as e:
        logger.error(f"Error running maintenance tasks: {str(e)}")


if __name__ == "__main__":
    # For testing purposes
    run_all_maintenance_tasks()
