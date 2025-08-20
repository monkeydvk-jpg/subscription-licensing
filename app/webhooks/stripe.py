"""
Stripe webhook handler for processing subscription events.
"""
import logging
from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..services.stripe_service import StripeService
from ..services.license_service import LicenseService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/stripe")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """Handle Stripe webhook events."""
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')
    
    if not sig_header:
        raise HTTPException(status_code=400, detail="Missing stripe signature")
    
    stripe_service = StripeService(db)
    event = stripe_service.construct_webhook_event(payload, sig_header)
    
    if not event:
        raise HTTPException(status_code=400, detail="Invalid webhook signature")
    
    try:
        # Handle different event types
        if event.type == 'checkout.session.completed':
            await handle_checkout_completed(event.data.object, db)
        
        elif event.type == 'customer.subscription.updated':
            await handle_subscription_updated(event.data.object, db)
        
        elif event.type == 'customer.subscription.deleted':
            await handle_subscription_deleted(event.data.object, db)
        
        elif event.type == 'invoice.payment_failed':
            await handle_invoice_payment_failed(event.data.object, db)
        
        elif event.type == 'invoice.payment_succeeded':
            await handle_invoice_payment_succeeded(event.data.object, db)
        
        else:
            logger.info(f"Unhandled event type: {event.type}")
    
    except Exception as e:
        logger.error(f"Error handling webhook {event.type}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
    
    return {"status": "success"}


async def handle_checkout_completed(session, db: Session):
    """Handle completed checkout session."""
    logger.info(f"Handling checkout completed: {session.id}")
    
    stripe_service = StripeService(db)
    license_service = LicenseService(db)
    
    # Create subscription record
    subscription = stripe_service.handle_checkout_completed(session)
    
    if subscription:
        # Create license for the user
        license = license_service.create_license_for_user(subscription.user_id)
        logger.info(f"Created license {license.id} for user {subscription.user_id}")
    else:
        logger.error(f"Failed to create subscription for session {session.id}")


async def handle_subscription_updated(subscription_data, db: Session):
    """Handle subscription status update."""
    logger.info(f"Handling subscription updated: {subscription_data.id}")
    
    stripe_service = StripeService(db)
    subscription = stripe_service.handle_subscription_updated(subscription_data)
    
    if subscription:
        logger.info(f"Updated subscription {subscription.id} status to {subscription.status}")
        
        # If subscription becomes inactive, consider suspending licenses
        if subscription.status.value in ['canceled', 'unpaid', 'past_due']:
            license_service = LicenseService(db)
            licenses = license_service.get_licenses_for_user(subscription.user_id)
            
            # Only suspend if subscription is permanently canceled or unpaid
            if subscription.status.value in ['canceled', 'unpaid']:
                for license in licenses:
                    if license.is_active and not license.is_suspended:
                        license_service.suspend_license(license.id)
                        logger.info(f"Suspended license {license.id} due to subscription status")


async def handle_subscription_deleted(subscription_data, db: Session):
    """Handle subscription cancellation."""
    logger.info(f"Handling subscription deleted: {subscription_data.id}")
    
    stripe_service = StripeService(db)
    success = stripe_service.handle_subscription_deleted(subscription_data)
    
    if success:
        # Find and suspend all licenses for this subscription's user
        license_service = LicenseService(db)
        
        # Get user from subscription
        from ..models import Subscription
        subscription = db.query(Subscription).filter(
            Subscription.stripe_subscription_id == subscription_data.id
        ).first()
        
        if subscription:
            licenses = license_service.get_licenses_for_user(subscription.user_id)
            for license in licenses:
                if license.is_active:
                    license_service.suspend_license(license.id)
                    logger.info(f"Suspended license {license.id} due to subscription deletion")


async def handle_invoice_payment_failed(invoice_data, db: Session):
    """Handle failed payment."""
    logger.info(f"Handling payment failed for invoice: {invoice_data.id}")
    
    stripe_service = StripeService(db)
    subscription = stripe_service.handle_invoice_payment_failed(invoice_data)
    
    if subscription:
        logger.info(f"Marked subscription {subscription.id} as past due")
        
        # Note: We don't immediately suspend licenses for past_due
        # Give users time to update payment method


async def handle_invoice_payment_succeeded(invoice_data, db: Session):
    """Handle successful payment."""
    logger.info(f"Handling payment succeeded for invoice: {invoice_data.id}")
    
    # If subscription was past due and now paid, reactivate licenses
    subscription_id = invoice_data.subscription
    
    if subscription_id:
        from ..models import Subscription, SubscriptionStatus
        
        subscription = db.query(Subscription).filter(
            Subscription.stripe_subscription_id == subscription_id
        ).first()
        
        if subscription and subscription.status == SubscriptionStatus.PAST_DUE:
            # Update subscription status to active
            stripe_service = StripeService(db)
            stripe_subscription = stripe_service.get_subscription_details(subscription_id)
            
            if stripe_subscription and stripe_subscription['status'] == 'active':
                subscription.status = SubscriptionStatus.ACTIVE
                db.commit()
                
                # Reactivate suspended licenses
                license_service = LicenseService(db)
                licenses = license_service.get_licenses_for_user(subscription.user_id)
                
                for license in licenses:
                    if license.is_suspended and not license.is_active:
                        license_service.activate_license(license.id)
                        logger.info(f"Reactivated license {license.id} after successful payment")
