"""
Main FastAPI application with all routes and endpoints.
"""
import logging
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Depends, Request, Form, status
from pydantic import BaseModel
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from .config import settings
from .database import get_db, create_tables
from .models import User, License, Subscription, AdminUser, SubscriptionStatus
from .schemas import (
    LicenseValidationRequest, LicenseValidationResponse, 
    CreateCheckoutRequest, CreateCheckoutResponse,
    Token, DashboardStats, LicenseListItem
)
from .services.license_service import LicenseService
from .services.stripe_service import StripeService
from .security import (
    verify_password, get_password_hash, create_access_token, 
    mask_license_key, is_license_key_format_valid
)
from .deps import get_current_admin_user, get_client_ip, get_user_agent
from .webhooks.stripe import router as stripe_webhook_router
from .utils import format_datetime, get_subscription_status_display

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Extension License Management System with Stripe Subscriptions"
)

# Create database tables (with error handling for serverless)
try:
    create_tables()
    logger.info("✅ Database tables initialized successfully")
except Exception as e:
    logger.error(f"⚠️ Database initialization failed: {e}")
    logger.info("Note: This might be expected in serverless environments. Tables will be created on first use.")

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Include webhook router
app.include_router(stripe_webhook_router, prefix="/webhooks")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page with basic information."""
    return templates.TemplateResponse("home.html", {
        "request": request,
        "app_name": settings.app_name
    })


@app.get("/success", response_class=HTMLResponse)
async def checkout_success(request: Request, session_id: Optional[str] = None):
    """Checkout success page."""
    return templates.TemplateResponse("success.html", {
        "request": request,
        "session_id": session_id,
        "app_name": settings.app_name
    })


@app.get("/cancel", response_class=HTMLResponse)
async def checkout_cancel(request: Request):
    """Checkout cancellation page."""
    return templates.TemplateResponse("cancel.html", {
        "request": request,
        "app_name": settings.app_name
    })


# Public API endpoints
@app.post("/api/checkout", response_model=CreateCheckoutResponse)
async def create_checkout_session(
    request: CreateCheckoutRequest,
    db: Session = Depends(get_db)
):
    """Create a Stripe checkout session for subscription."""
    try:
        stripe_service = StripeService(db)
        result = stripe_service.create_checkout_session(
            email=request.email,
            success_url=request.success_url,
            cancel_url=request.cancel_url
        )
        
        return CreateCheckoutResponse(checkout_url=result['checkout_url'])
        
    except Exception as e:
        logger.error(f"Error creating checkout session: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create checkout session")


@app.post("/api/validate", response_model=LicenseValidationResponse)
async def validate_license(
    request: LicenseValidationRequest,
    http_request: Request,
    db: Session = Depends(get_db),
    client_ip: str = Depends(get_client_ip),
    user_agent: str = Depends(get_user_agent)
):
    """Validate a license key."""
    
    # Basic format validation
    if not is_license_key_format_valid(request.license_key):
        return LicenseValidationResponse(
            valid=False,
            message="Invalid license key format",
            error_code="INVALID_KEY"
        )
    
    license_service = LicenseService(db)
    
    try:
        response = license_service.validate_license(
            license_key=request.license_key,
            ip_address=client_ip,
            user_agent=user_agent,
            extension_version=request.extension_version,
            device_fingerprint=request.device_fingerprint
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error validating license: {str(e)}")
        return LicenseValidationResponse(
            valid=False,
            message="Validation service unavailable",
            error_code="SERVICE_ERROR"
        )


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    from .config import settings
    db_url = settings.effective_database_url
    db_type = "PostgreSQL" if "postgres" in db_url else "SQLite"
    
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.app_version,
        "database_type": db_type,
        "database_url_preview": db_url[:50] + ("..." if len(db_url) > 50 else "")
    }


@app.get("/api/debug/db-env")
async def debug_db_env():
    """Debug endpoint to check database environment."""
    import os
    from .config import settings
    
    db_url = settings.effective_database_url
    db_type = "PostgreSQL" if "postgres" in db_url else "SQLite"
    
    env_vars = {
        key: value[:50] + ("..." if len(value) > 50 else "")
        for key, value in os.environ.items()
        if key.upper().startswith(("DATABASE", "POSTGRES"))
    }
    
    return {
        "effective_database_url": db_url[:50] + ("..." if len(db_url) > 50 else ""),
        "database_type": db_type,
        "environment_variables": env_vars,
    }


@app.post("/api/debug/reset-db")
async def reset_database():
    """Force database initialization (DANGEROUS - USE ONLY FOR DEBUGGING)."""
    try:
        from .database import get_engine
        from .models import Base, AdminUser
        from .security import get_password_hash
        from sqlalchemy.orm import sessionmaker
        
        # Get fresh engine
        engine = get_engine()
        
        # Drop and recreate all tables
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        
        # Create admin user
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        try:
            admin_user = AdminUser(
                username=settings.admin_username,
                hashed_password=get_password_hash(settings.admin_password),
                is_active=True
            )
            db.add(admin_user)
            db.commit()
        finally:
            db.close()
        
        return {
            "success": True,
            "message": "Database reset completed",
            "database_type": "PostgreSQL" if "postgres" in settings.effective_database_url else "SQLite"
        }
        
    except Exception as e:
        logger.error(f"Database reset failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "Database reset failed"
        }


@app.get("/api/debug/admin-info")
async def get_admin_info():
    """Get admin user information for debugging."""
    import os
    try:
        return {
            "configured_username": settings.admin_username,
            "configured_password": "***" + settings.admin_password[-2:] if len(settings.admin_password) > 2 else "***",
            "password_length": len(settings.admin_password),
            "admin_username_env": os.getenv('ADMIN_USERNAME', 'not_set'),
            "admin_password_env": "***" + (os.getenv('ADMIN_PASSWORD', '')[-2:] if os.getenv('ADMIN_PASSWORD') and len(os.getenv('ADMIN_PASSWORD')) > 2 else 'not_set')
        }
    except Exception as e:
        return {"error": str(e)}


@app.post("/api/debug/reset-admin")
async def reset_admin_user():
    """Reset admin user with default credentials."""
    try:
        from .models import AdminUser
        from .security import get_password_hash
        
        db = next(get_db())
        try:
            # Delete existing admin user
            existing_admin = db.query(AdminUser).filter(AdminUser.username == "admin").first()
            if existing_admin:
                db.delete(existing_admin)
                db.commit()
            
            # Create new admin user with hardcoded credentials
            admin_user = AdminUser(
                username="admin",
                hashed_password=get_password_hash("changeme"),
                is_active=True
            )
            db.add(admin_user)
            db.commit()
            
            return {
                "success": True,
                "message": "Admin user reset to admin/changeme",
                "username": "admin",
                "password": "changeme"
            }
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Admin user reset failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "Admin user reset failed"
        }


# Admin Authentication
@app.post("/api/admin/login", response_model=Token)
async def admin_login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Admin login endpoint."""
    logger.info(f"Login attempt for user: {form_data.username}")
    
    user = db.query(AdminUser).filter(AdminUser.username == form_data.username).first()
    
    if not user:
        logger.error(f"User not found: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    logger.info(f"User found: {user.username}, active: {user.is_active}")
    
    password_valid = verify_password(form_data.password, user.hashed_password)
    logger.info(f"Password verification result: {password_valid}")
    
    if not password_valid:
        logger.error(f"Password verification failed for user: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        logger.error(f"User is inactive: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    logger.info(f"Login successful for user: {form_data.username}")
    access_token = create_access_token(data={"sub": user.username})
    return Token(access_token=access_token, token_type="bearer")


# Admin UI Routes
@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    """Admin dashboard page."""
    return templates.TemplateResponse("admin.html", {
        "request": request,
        "app_name": settings.app_name,
        "stripe_publishable_key": settings.stripe_publishable_key
    })


@app.get("/admin/login", response_class=HTMLResponse)
async def admin_login_page(request: Request):
    """Admin login page."""
    return templates.TemplateResponse("admin_login.html", {
        "request": request,
        "app_name": settings.app_name
    })


# Admin API endpoints
@app.get("/api/admin/dashboard", response_model=DashboardStats)
async def get_dashboard_stats(
    current_user: AdminUser = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get dashboard statistics."""
    try:
        # Count total users
        total_users = db.query(User).count()
        
        # Count active licenses
        active_licenses = db.query(License).filter(
            License.is_active == True,
            License.is_suspended == False
        ).count()
        
        # Count active subscriptions
        active_subscriptions = db.query(Subscription).filter(
            Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING])
        ).count()
        
        # Calculate monthly revenue (this is a simplified calculation)
        # In production, you'd want to integrate with Stripe's reporting API
        monthly_revenue = active_subscriptions * 29.99  # Assuming $29.99/month
        
        return DashboardStats(
            total_users=total_users,
            active_licenses=active_licenses,
            active_subscriptions=active_subscriptions,
            monthly_revenue=monthly_revenue
        )
        
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get dashboard stats")


@app.get("/api/admin/licenses", response_model=List[LicenseListItem])
async def get_licenses(
    current_user: AdminUser = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """Get list of licenses."""
    try:
        licenses = db.query(License).join(User).offset(skip).limit(limit).all()
        
        result = []
        for license in licenses:
            # Get subscription status
            subscription = db.query(Subscription).filter(
                Subscription.user_id == license.user_id,
                Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING])
            ).first()
            
            subscription_status = None
            if subscription:
                subscription_status = subscription.status.value
            
            result.append(LicenseListItem(
                id=license.id,
                license_key=mask_license_key(license.license_key),
                user_email=license.user.email,
                is_active=license.is_active,
                is_suspended=license.is_suspended,
                created_at=license.created_at,
                last_validated=license.last_validated,
                subscription_status=subscription_status
            ))
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting licenses: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get licenses")


@app.get("/api/admin/active-licenses")
async def get_active_licenses(
    current_user: AdminUser = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get currently active licenses with real-time status."""
    try:
        # Get licenses that have been validated recently (within last 24 hours)
        recently_validated = db.query(License).join(User).filter(
            License.is_active == True,
            License.is_suspended == False,
            License.last_validated != None,
            License.last_validated >= datetime.utcnow() - timedelta(hours=24)
        ).all()
        
        active_licenses = []
        for license in recently_validated:
            # Get subscription status
            subscription = db.query(Subscription).filter(
                Subscription.user_id == license.user_id,
                Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING])
            ).first()
            
            if subscription:  # Only include licenses with active subscriptions
                active_licenses.append({
                    "id": license.id,
                    "license_key": mask_license_key(license.license_key),
                    "user_email": license.user.email,
                    "last_validated": license.last_validated,
                    "validation_count": license.validation_count,
                    "device_fingerprint": license.device_fingerprint,
                    "extension_version": license.extension_version,
                    "last_ip": license.last_ip,
                    "subscription_status": subscription.status.value,
                    "subscription_expires": subscription.current_period_end
                })
        
        return {
            "total_active": len(active_licenses),
            "licenses": active_licenses,
            "last_updated": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting active licenses: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get active licenses")


@app.post("/api/admin/licenses")
async def create_license(
    email: str = Form(...),
    current_user: AdminUser = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Create a new license for a user."""
    try:
        # Get or create user
        user = db.query(User).filter(User.email == email).first()
        if not user:
            user = User(email=email)
            db.add(user)
            db.commit()
            db.refresh(user)
        
        # Create license
        license_service = LicenseService(db)
        license = license_service.create_license_for_user(user.id)
        
        return {
            "success": True,
            "license_id": license.id,
            "license_key": license.license_key,
            "message": f"License created for {email}"
        }
        
    except Exception as e:
        logger.error(f"Error creating license: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create license")


@app.post("/api/admin/licenses/{license_id}/suspend")
async def suspend_license(
    license_id: int,
    current_user: AdminUser = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Suspend a license."""
    try:
        license_service = LicenseService(db)
        success = license_service.suspend_license(license_id)
        
        if success:
            return {"success": True, "message": "License suspended"}
        else:
            raise HTTPException(status_code=404, detail="License not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error suspending license: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to suspend license")


@app.post("/api/admin/licenses/{license_id}/activate")
async def activate_license(
    license_id: int,
    current_user: AdminUser = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Activate a suspended license."""
    try:
        license_service = LicenseService(db)
        success = license_service.activate_license(license_id)
        
        if success:
            return {"success": True, "message": "License activated"}
        else:
            raise HTTPException(status_code=404, detail="License not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error activating license: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to activate license")


@app.post("/api/admin/licenses/{license_id}/deactivate")
async def deactivate_license(
    license_id: int,
    current_user: AdminUser = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Deactivate a license."""
    try:
        license_service = LicenseService(db)
        success = license_service.deactivate_license(license_id)
        
        if success:
            return {"success": True, "message": "License deactivated"}
        else:
            raise HTTPException(status_code=404, detail="License not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deactivating license: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to deactivate license")


@app.post("/api/admin/licenses/{license_id}/rotate")
async def rotate_license_key(
    license_id: int,
    current_user: AdminUser = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Generate new license key for existing license."""
    try:
        license_service = LicenseService(db)
        new_key = license_service.rotate_license_key(license_id)
        
        if new_key:
            return {
                "success": True, 
                "new_license_key": new_key,
                "message": "License key rotated"
            }
        else:
            raise HTTPException(status_code=404, detail="License not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rotating license key: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to rotate license key")


@app.delete("/api/admin/licenses/{license_id}")
async def delete_license(
    license_id: int,
    current_user: AdminUser = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Delete a license permanently."""
    try:
        # Find the license
        license = db.query(License).filter(License.id == license_id).first()
        
        if not license:
            raise HTTPException(status_code=404, detail="License not found")
        
        # Get user info for the response
        user_email = license.user.email if license.user else "unknown"
        license_key_masked = mask_license_key(license.license_key)
        
        # Delete the license
        db.delete(license)
        db.commit()
        
        logger.info(f"License {license_id} deleted by admin {current_user.username}")
        
        return {
            "success": True,
            "message": f"License {license_key_masked} for {user_email} has been deleted",
            "deleted_license_id": license_id,
            "user_email": user_email
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting license {license_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete license")


# Subscription Management Endpoints
@app.get("/api/admin/subscriptions")
async def get_subscriptions(
    current_user: AdminUser = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """Get list of subscriptions."""
    try:
        subscriptions = db.query(Subscription).join(User).offset(skip).limit(limit).all()
        
        result = []
        for sub in subscriptions:
            # Use the stored plan name, fallback to determining from subscription ID
            plan_name = sub.plan_name or ("premium" if "premium" in (sub.stripe_subscription_id or "").lower() else "basic")
            amount = 29.99 if plan_name.lower() == "premium" else 9.99
            
            # Calculate days until expiry - prioritize end_time over current_period_end
            days_until_expiry = None
            expiration_status = "unknown"
            
            # Determine effective expiration date
            effective_expiry = None
            if sub.end_time:
                effective_expiry = sub.end_time  # end_time takes precedence
            elif sub.current_period_end:
                effective_expiry = sub.current_period_end  # fallback to current_period_end
            
            if effective_expiry:
                days_diff = (effective_expiry - datetime.utcnow()).days
                days_until_expiry = days_diff
                
                if days_diff < 0:
                    expiration_status = "expired"
                elif days_diff <= 7:
                    expiration_status = "expires_soon"
                else:
                    expiration_status = "active"
            
            # Check if in trial
            is_trial = (sub.trial_end and sub.trial_end > datetime.utcnow()) or sub.status == SubscriptionStatus.TRIALING
            
            result.append({
                "id": sub.id,
                "stripe_subscription_id": sub.stripe_subscription_id,
                "user_email": sub.user.email,
                "user_id": sub.user_id,
                "plan_name": plan_name,
                "billing_cycle": sub.billing_cycle or "monthly",
                "amount": amount,
                "status": sub.status.value if sub.status else None,
                "current_period_start": sub.current_period_start,
                "current_period_end": sub.current_period_end,
                "end_time": sub.end_time,
                "trial_end": sub.trial_end,
                "cancel_at_period_end": sub.cancel_at_period_end,
                "days_until_expiry": days_until_expiry,
                "expiration_status": expiration_status,
                "is_trial": is_trial,
                "created_at": sub.created_at,
                "updated_at": sub.updated_at
            })
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting subscriptions: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get subscriptions")


# Helper function to map status values
def map_status_to_enum(status_str: str) -> SubscriptionStatus:
    """Map status string to SubscriptionStatus enum value."""
    status_mapping = {
        'active': SubscriptionStatus.ACTIVE,
        'trialing': SubscriptionStatus.TRIALING,
        'past_due': SubscriptionStatus.PAST_DUE,
        'canceled': SubscriptionStatus.CANCELED,
        'cancelled': SubscriptionStatus.CANCELED,  # Handle both spellings
        'unpaid': SubscriptionStatus.UNPAID,
        'incomplete': SubscriptionStatus.INCOMPLETE,
        'incomplete_expired': SubscriptionStatus.INCOMPLETE_EXPIRED,
        'ended': SubscriptionStatus.ENDED,
        # Also handle uppercase versions
        'ACTIVE': SubscriptionStatus.ACTIVE,
        'TRIALING': SubscriptionStatus.TRIALING,
        'PAST_DUE': SubscriptionStatus.PAST_DUE,
        'CANCELED': SubscriptionStatus.CANCELED,
        'CANCELLED': SubscriptionStatus.CANCELED,
        'UNPAID': SubscriptionStatus.UNPAID,
        'INCOMPLETE': SubscriptionStatus.INCOMPLETE,
        'INCOMPLETE_EXPIRED': SubscriptionStatus.INCOMPLETE_EXPIRED,
        'ENDED': SubscriptionStatus.ENDED,
    }
    
    if status_str in status_mapping:
        return status_mapping[status_str]
    else:
        # Default to ACTIVE if unknown status
        logger.warning(f"Unknown status: {status_str}, defaulting to ACTIVE")
        return SubscriptionStatus.ACTIVE

# Pydantic models for subscription requests
class CreateSubscriptionRequest(BaseModel):
    user_email: str
    plan_name: str = "basic"
    amount: float = 9.99
    status: str = "active"

class UpdateSubscriptionRequest(BaseModel):
    user_email: str
    plan_name: str
    amount: float
    status: str

@app.get("/api/admin/subscriptions/{subscription_id}")
async def get_subscription(
    subscription_id: int,
    current_user: AdminUser = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get a specific subscription by ID."""
    try:
        subscription = db.query(Subscription).join(User).filter(Subscription.id == subscription_id).first()
        
        if not subscription:
            raise HTTPException(status_code=404, detail="Subscription not found")
        
        return {
            "id": subscription.id,
            "stripe_subscription_id": subscription.stripe_subscription_id,
            "user_email": subscription.user.email,
            "user_id": subscription.user_id,
            "plan_name": subscription.plan_name or ("premium" if "premium" in (subscription.stripe_subscription_id or "").lower() else "basic"),
            "billing_cycle": subscription.billing_cycle or "monthly",
            "amount": 29.99 if "premium" in (subscription.stripe_subscription_id or "").lower() else 9.99,
            "status": subscription.status.value if subscription.status else "active",
            "current_period_start": subscription.current_period_start,
            "current_period_end": subscription.current_period_end,
            "end_time": subscription.end_time,
            "trial_end": subscription.trial_end,
            "cancel_at_period_end": subscription.cancel_at_period_end,
            "created_at": subscription.created_at,
            "updated_at": subscription.updated_at
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting subscription: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get subscription")

@app.post("/api/admin/subscriptions")
async def create_subscription(
    request: CreateSubscriptionRequest,
    current_user: AdminUser = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Create a new subscription for a user."""
    try:
        # Get or create user
        user = db.query(User).filter(User.email == request.user_email).first()
        if not user:
            user = User(email=request.user_email)
            db.add(user)
            db.commit()
            db.refresh(user)
        
        # Create subscription with plan info
        plan_prefix = "premium" if request.plan_name.lower() == "premium" else "basic"
        subscription = Subscription(
            stripe_subscription_id=f"manual_{plan_prefix}_sub_{user.id}_{int(datetime.utcnow().timestamp())}",
            user_id=user.id,
            status=map_status_to_enum(request.status),
            current_period_start=datetime.utcnow(),
            current_period_end=datetime.utcnow() + timedelta(days=30),
            cancel_at_period_end=False
        )
        
        db.add(subscription)
        db.commit()
        db.refresh(subscription)
        
        return {
            "success": True,
            "subscription_id": subscription.id,
            "message": f"Subscription created for {request.user_email}"
        }
        
    except Exception as e:
        logger.error(f"Error creating subscription: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create subscription: {str(e)}")


@app.put("/api/admin/subscriptions/{subscription_id}")
async def update_subscription(
    subscription_id: int,
    request: UpdateSubscriptionRequest,
    current_user: AdminUser = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Update subscription details."""
    try:
        subscription = db.query(Subscription).filter(Subscription.id == subscription_id).first()
        
        if not subscription:
            raise HTTPException(status_code=404, detail="Subscription not found")
        
        # Update fields
        subscription.status = map_status_to_enum(request.status)
        
        # Update user email if changed
        if subscription.user.email != request.user_email:
            user = db.query(User).filter(User.email == request.user_email).first()
            if not user:
                user = User(email=request.user_email)
                db.add(user)
                db.commit()
                db.refresh(user)
            subscription.user_id = user.id
        
        # Update stripe subscription ID to reflect plan change
        plan_prefix = "premium" if request.plan_name.lower() == "premium" else "basic"
        if not subscription.stripe_subscription_id.startswith(f"manual_{plan_prefix}"):
            subscription.stripe_subscription_id = f"manual_{plan_prefix}_sub_{subscription.user_id}_{int(datetime.utcnow().timestamp())}"
        
        subscription.updated_at = datetime.utcnow()
        
        db.commit()
        
        return {
            "success": True,
            "message": "Subscription updated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating subscription: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update subscription")


@app.delete("/api/admin/subscriptions/{subscription_id}")
async def delete_subscription(
    subscription_id: int,
    current_user: AdminUser = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Delete a subscription."""
    try:
        subscription = db.query(Subscription).filter(Subscription.id == subscription_id).first()
        
        if not subscription:
            raise HTTPException(status_code=404, detail="Subscription not found")
        
        db.delete(subscription)
        db.commit()
        
        return {
            "success": True,
            "message": "Subscription deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting subscription: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete subscription")


class SetEndTimeRequest(BaseModel):
    end_time: Optional[str] = None  # ISO datetime string or None to clear


@app.post("/api/admin/subscriptions/{subscription_id}/set-end-time")
async def set_subscription_end_time(
    subscription_id: int,
    request: SetEndTimeRequest,
    current_user: AdminUser = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Set or clear the end_time for a subscription."""
    try:
        subscription = db.query(Subscription).filter(Subscription.id == subscription_id).first()
        
        if not subscription:
            raise HTTPException(status_code=404, detail="Subscription not found")
        
        # Parse and set end_time
        if request.end_time:
            try:
                # Parse ISO datetime string
                subscription.end_time = datetime.fromisoformat(request.end_time.replace('Z', '+00:00'))
                message = f"End time set to {subscription.end_time}"
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid datetime format. Use ISO format (YYYY-MM-DDTHH:MM:SS)")
        else:
            # Clear end_time
            subscription.end_time = None
            message = "End time cleared - will use current_period_end"
        
        subscription.updated_at = datetime.utcnow()
        db.commit()
        
        return {
            "success": True,
            "message": message,
            "end_time": subscription.end_time.isoformat() if subscription.end_time else None,
            "current_period_end": subscription.current_period_end.isoformat() if subscription.current_period_end else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting subscription end_time: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to set subscription end_time")


# Initialize admin user on startup
@app.on_event("startup")
async def create_admin_user():
    """Create default admin user if it doesn't exist."""
    db = next(get_db())
    try:
        admin_user = db.query(AdminUser).filter(AdminUser.username == settings.admin_username).first()
        
        if not admin_user:
            admin_user = AdminUser(
                username=settings.admin_username,
                hashed_password=get_password_hash(settings.admin_password),
                is_active=True
            )
            db.add(admin_user)
            db.commit()
            logger.info(f"Created default admin user: {settings.admin_username}")
        
    except Exception as e:
        logger.error(f"Error creating admin user: {str(e)}")
    finally:
        db.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
