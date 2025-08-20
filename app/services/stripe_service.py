"""
Stripe service for handling payments and subscriptions.
"""
import stripe
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from ..models import User, Subscription, SubscriptionStatus
from ..config import settings

# Configure Stripe
stripe.api_key = settings.stripe_secret_key


class StripeService:
    def __init__(self, db: Session):
        self.db = db

    def create_checkout_session(
        self, 
        email: str, 
        success_url: Optional[str] = None, 
        cancel_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a Stripe Checkout session for subscription."""
        
        # Create or get customer
        customer = self._get_or_create_customer(email)
        
        # Set default URLs if not provided
        if not success_url:
            success_url = settings.success_url
        if not cancel_url:
            cancel_url = settings.cancel_url
        
        try:
            checkout_session = stripe.checkout.Session.create(
                customer=customer.id,
                payment_method_types=['card'],
                line_items=[{
                    'price': settings.stripe_price_id,
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=success_url + '?session_id={CHECKOUT_SESSION_ID}',
                cancel_url=cancel_url,
                automatic_tax={'enabled': True},
                billing_address_collection='required',
                customer_update={
                    'address': 'auto',
                    'name': 'auto'
                }
            )
            
            return {
                'checkout_url': checkout_session.url,
                'session_id': checkout_session.id
            }
            
        except stripe.error.StripeError as e:
            raise Exception(f"Failed to create checkout session: {str(e)}")

    def create_customer_portal_session(self, customer_id: str, return_url: str) -> str:
        """Create a customer portal session for subscription management."""
        try:
            portal_session = stripe.billing_portal.Session.create(
                customer=customer_id,
                return_url=return_url,
            )
            return portal_session.url
        except stripe.error.StripeError as e:
            raise Exception(f"Failed to create portal session: {str(e)}")

    def handle_checkout_completed(self, session: Dict[str, Any]) -> Optional[Subscription]:
        """Handle successful checkout completion."""
        customer_id = session.get('customer')
        subscription_id = session.get('subscription')
        
        if not customer_id or not subscription_id:
            return None
        
        # Get user by customer ID
        user = self.db.query(User).filter(User.stripe_customer_id == customer_id).first()
        if not user:
            return None
        
        # Get subscription details from Stripe
        try:
            stripe_subscription = stripe.Subscription.retrieve(subscription_id)
            
            # Create subscription record
            subscription = Subscription(
                stripe_subscription_id=subscription_id,
                user_id=user.id,
                status=SubscriptionStatus(stripe_subscription.status),
                current_period_start=datetime.fromtimestamp(stripe_subscription.current_period_start),
                current_period_end=datetime.fromtimestamp(stripe_subscription.current_period_end),
                cancel_at_period_end=stripe_subscription.cancel_at_period_end
            )
            
            self.db.add(subscription)
            self.db.commit()
            self.db.refresh(subscription)
            
            return subscription
            
        except stripe.error.StripeError:
            return None

    def handle_subscription_updated(self, subscription_data: Dict[str, Any]) -> Optional[Subscription]:
        """Handle subscription status updates."""
        subscription_id = subscription_data.get('id')
        
        # Find existing subscription
        subscription = self.db.query(Subscription).filter(
            Subscription.stripe_subscription_id == subscription_id
        ).first()
        
        if not subscription:
            return None
        
        # Update subscription details
        subscription.status = SubscriptionStatus(subscription_data.get('status'))
        subscription.current_period_start = datetime.fromtimestamp(
            subscription_data.get('current_period_start')
        )
        subscription.current_period_end = datetime.fromtimestamp(
            subscription_data.get('current_period_end')
        )
        subscription.cancel_at_period_end = subscription_data.get('cancel_at_period_end', False)
        
        self.db.commit()
        return subscription

    def handle_subscription_deleted(self, subscription_data: Dict[str, Any]) -> bool:
        """Handle subscription cancellation/deletion."""
        subscription_id = subscription_data.get('id')
        
        subscription = self.db.query(Subscription).filter(
            Subscription.stripe_subscription_id == subscription_id
        ).first()
        
        if subscription:
            subscription.status = SubscriptionStatus.CANCELED
            self.db.commit()
            return True
        
        return False

    def handle_invoice_payment_failed(self, invoice_data: Dict[str, Any]) -> Optional[Subscription]:
        """Handle failed invoice payment."""
        subscription_id = invoice_data.get('subscription')
        
        if subscription_id:
            subscription = self.db.query(Subscription).filter(
                Subscription.stripe_subscription_id == subscription_id
            ).first()
            
            if subscription:
                subscription.status = SubscriptionStatus.PAST_DUE
                self.db.commit()
                return subscription
        
        return None

    def get_subscription_details(self, subscription_id: str) -> Optional[Dict[str, Any]]:
        """Get subscription details from Stripe."""
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            return {
                'id': subscription.id,
                'status': subscription.status,
                'current_period_start': subscription.current_period_start,
                'current_period_end': subscription.current_period_end,
                'cancel_at_period_end': subscription.cancel_at_period_end,
                'canceled_at': subscription.canceled_at,
                'customer': subscription.customer
            }
        except stripe.error.StripeError:
            return None

    def cancel_subscription(self, subscription_id: str) -> bool:
        """Cancel a subscription at period end."""
        try:
            stripe.Subscription.modify(
                subscription_id,
                cancel_at_period_end=True
            )
            return True
        except stripe.error.StripeError:
            return False

    def reactivate_subscription(self, subscription_id: str) -> bool:
        """Reactivate a subscription (remove cancellation)."""
        try:
            stripe.Subscription.modify(
                subscription_id,
                cancel_at_period_end=False
            )
            return True
        except stripe.error.StripeError:
            return False

    def _get_or_create_customer(self, email: str) -> stripe.Customer:
        """Get existing customer or create new one."""
        # Check if user exists in database
        user = self.db.query(User).filter(User.email == email).first()
        
        if user and user.stripe_customer_id:
            try:
                # Verify customer exists in Stripe
                customer = stripe.Customer.retrieve(user.stripe_customer_id)
                return customer
            except stripe.error.StripeError:
                # Customer doesn't exist in Stripe, create new one
                pass
        
        # Create new customer
        try:
            customer = stripe.Customer.create(email=email)
            
            # Create or update user record
            if not user:
                user = User(email=email, stripe_customer_id=customer.id)
                self.db.add(user)
            else:
                user.stripe_customer_id = customer.id
            
            self.db.commit()
            return customer
            
        except stripe.error.StripeError as e:
            raise Exception(f"Failed to create customer: {str(e)}")

    def construct_webhook_event(self, payload: bytes, sig_header: str) -> Optional[stripe.Event]:
        """Construct and verify webhook event."""
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.stripe_webhook_secret
            )
            return event
        except ValueError:
            # Invalid payload
            return None
        except stripe.error.SignatureVerificationError:
            # Invalid signature
            return None
