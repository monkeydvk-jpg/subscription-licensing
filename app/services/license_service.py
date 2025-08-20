"""
License service for managing license keys and validation.
"""
from datetime import datetime, timedelta
from typing import Optional, Tuple
from sqlalchemy.orm import Session

from ..models import User, License, Subscription, SubscriptionStatus, ApiLog
from ..security import generate_license_key, hash_license_key, verify_license_key
from ..schemas import LicenseValidationResponse
from ..utils import is_subscription_active


class LicenseService:
    def __init__(self, db: Session):
        self.db = db

    def create_license_for_user(self, user_id: int) -> License:
        """Create a new license for a user."""
        # Generate unique license key
        while True:
            license_key = generate_license_key()
            license_key_hash = hash_license_key(license_key)
            
            # Check if hash already exists (very unlikely but worth checking)
            existing = self.db.query(License).filter(License.license_key_hash == license_key_hash).first()
            if not existing:
                break

        # Create license
        license = License(
            license_key=license_key,
            license_key_hash=license_key_hash,
            user_id=user_id,
            is_active=True,
            is_suspended=False
        )
        
        self.db.add(license)
        self.db.commit()
        self.db.refresh(license)
        
        return license

    def validate_license(
        self, 
        license_key: str, 
        ip_address: str = "unknown",
        user_agent: str = "unknown",
        extension_version: Optional[str] = None,
        device_fingerprint: Optional[str] = None
    ) -> LicenseValidationResponse:
        """Validate a license key and return validation response."""
        
        # Log the validation attempt
        self._log_api_call(license_key, "validate", ip_address, user_agent)
        
        # Find license by hash
        license_key_hash = hash_license_key(license_key)
        license = self.db.query(License).filter(License.license_key_hash == license_key_hash).first()
        
        if not license:
            return LicenseValidationResponse(
                valid=False,
                message="Invalid license key",
                error_code="INVALID_KEY"
            )
        
        # Check if license is active
        if not license.is_active:
            return LicenseValidationResponse(
                valid=False,
                message="License key is inactive",
                error_code="INACTIVE"
            )
        
        # Check if license is suspended
        if license.is_suspended:
            return LicenseValidationResponse(
                valid=False,
                message="License key is suspended.",
                error_code="SUSPENDED",
                expires_at=None,
                subscription_status=None
            )
        user = license.user
        # Get any subscription for the user (not just active ones)
        subscription = self._get_subscription_for_user(user.id)
        
        if not subscription:
            return LicenseValidationResponse(
                valid=False,
                message="No active subscription found",
                error_code="NO_SUBSCRIPTION"
            )
        
        # Check subscription status
        if not is_subscription_active(subscription.status.value):
            return LicenseValidationResponse(
                valid=False,
                message=f"Subscription is {subscription.status.value}",
                error_code="SUBSCRIPTION_INACTIVE",
                subscription_status=subscription.status.value
            )
        
        # Update license metadata
        self._update_license_metadata(
            license, 
            ip_address, 
            extension_version, 
            device_fingerprint
        )
        
        # Calculate days until expiry - use end_time if available, otherwise current_period_end
        days_until_expiry = None
        next_renewal_date = None
        effective_expiry = subscription.end_time or subscription.current_period_end
        
        if effective_expiry:
            days_until_expiry = (effective_expiry - datetime.utcnow()).days
            # Next renewal date is the current period end (unless canceled)
            if not subscription.cancel_at_period_end:
                next_renewal_date = subscription.current_period_end
        
        # Determine subscription plan display name
        plan_display = subscription.plan_name or "Unknown Plan"
        if subscription.billing_cycle:
            plan_display += f" ({subscription.billing_cycle.capitalize()})"
        
        return LicenseValidationResponse(
            valid=True,
            message="License key is valid",
            error_code=None,  # No error code for successful validation
            expires_at=effective_expiry,  # Use end_time if available, otherwise current_period_end
            subscription_status=subscription.status.value,
            current_period_start=subscription.current_period_start,
            current_period_end=subscription.current_period_end,
            end_time=subscription.end_time,
            next_renewal_date=next_renewal_date,
            cancel_at_period_end=subscription.cancel_at_period_end,
            subscription_plan=plan_display,
            days_until_expiry=days_until_expiry
        )

    def suspend_license(self, license_id: int) -> bool:
        """Suspend a license."""
        license = self.db.query(License).filter(License.id == license_id).first()
        if license:
            license.is_suspended = True
            self.db.commit()
            return True
        return False

    def activate_license(self, license_id: int) -> bool:
        """Activate a suspended license."""
        license = self.db.query(License).filter(License.id == license_id).first()
        if license:
            license.is_suspended = False
            license.is_active = True
            self.db.commit()
            return True
        return False

    def deactivate_license(self, license_id: int) -> bool:
        """Deactivate a license."""
        license = self.db.query(License).filter(License.id == license_id).first()
        if license:
            license.is_active = False
            self.db.commit()
            return True
        return False

    def rotate_license_key(self, license_id: int) -> Optional[str]:
        """Generate a new license key for an existing license."""
        license = self.db.query(License).filter(License.id == license_id).first()
        if not license:
            return None
        
        # Generate new unique license key
        while True:
            new_license_key = generate_license_key()
            new_license_key_hash = hash_license_key(new_license_key)
            
            existing = self.db.query(License).filter(License.license_key_hash == new_license_key_hash).first()
            if not existing:
                break
        
        # Update license
        license.license_key = new_license_key
        license.license_key_hash = new_license_key_hash
        self.db.commit()
        
        return new_license_key

    def get_license_by_id(self, license_id: int) -> Optional[License]:
        """Get license by ID."""
        return self.db.query(License).filter(License.id == license_id).first()

    def get_licenses_for_user(self, user_id: int) -> list[License]:
        """Get all licenses for a user."""
        return self.db.query(License).filter(License.user_id == user_id).all()

    def _get_active_subscription(self, user_id: int) -> Optional[Subscription]:
        """Get active subscription for user."""
        return self.db.query(Subscription).filter(
            Subscription.user_id == user_id,
            Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING])
        ).first()

    def _get_subscription_for_user(self, user_id: int) -> Optional[Subscription]:
        """Get any subscription for user (including inactive ones)."""
        return self.db.query(Subscription).filter(
            Subscription.user_id == user_id
        ).order_by(Subscription.created_at.desc()).first()

    def _update_license_metadata(
        self, 
        license: License, 
        ip_address: str,
        extension_version: Optional[str] = None,
        device_fingerprint: Optional[str] = None
    ):
        """Update license metadata after validation."""
        license.last_validated = datetime.utcnow()
        license.last_ip = ip_address
        license.validation_count += 1
        
        if extension_version:
            license.extension_version = extension_version
            
        if device_fingerprint:
            license.device_fingerprint = device_fingerprint
        
        self.db.commit()

    def _log_api_call(self, license_key: str, endpoint: str, ip_address: str, user_agent: str):
        """Log API call for analytics."""
        try:
            license_key_hash = hash_license_key(license_key)
            
            log_entry = ApiLog(
                license_key_hash=license_key_hash,
                endpoint=endpoint,
                method="POST",
                status_code=200,  # Will be updated if validation fails
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            self.db.add(log_entry)
            self.db.commit()
        except Exception:
            # Don't let logging errors break the main flow
            self.db.rollback()
