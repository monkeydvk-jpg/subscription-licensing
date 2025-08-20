"""
Pydantic schemas for API requests and responses.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr

from .models import SubscriptionStatus


# Base schemas
class UserBase(BaseModel):
    email: EmailStr


class UserCreate(UserBase):
    pass


class User(UserBase):
    id: int
    stripe_customer_id: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


# License schemas
class LicenseBase(BaseModel):
    pass


class LicenseCreate(LicenseBase):
    user_id: int


class License(LicenseBase):
    id: int
    license_key: str
    user_id: int
    is_active: bool
    is_suspended: bool
    created_at: datetime
    last_validated: Optional[datetime]
    expires_at: Optional[datetime]
    extension_version: Optional[str]
    device_fingerprint: Optional[str]
    last_ip: Optional[str]
    validation_count: int
    
    model_config = {"from_attributes": True}


class LicenseValidationRequest(BaseModel):
    license_key: str
    extension_version: Optional[str] = None
    device_fingerprint: Optional[str] = None


class LicenseValidationResponse(BaseModel):
    valid: bool
    message: str
    error_code: Optional[str] = None  # For programmatic handling by extensions
    expires_at: Optional[datetime] = None
    subscription_status: Optional[str] = None
    # Additional subscription details
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    end_time: Optional[datetime] = None
    next_renewal_date: Optional[datetime] = None
    cancel_at_period_end: Optional[bool] = None
    subscription_plan: Optional[str] = None
    days_until_expiry: Optional[int] = None


# Subscription schemas
class SubscriptionBase(BaseModel):
    pass


class Subscription(SubscriptionBase):
    id: int
    stripe_subscription_id: str
    user_id: int
    status: SubscriptionStatus
    current_period_start: Optional[datetime]
    current_period_end: Optional[datetime]
    end_time: Optional[datetime]
    cancel_at_period_end: bool
    stripe_price_id: Optional[str]
    plan_name: Optional[str]
    billing_cycle: Optional[str]
    trial_end: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


# Admin schemas
class AdminUserBase(BaseModel):
    username: str


class AdminUserCreate(AdminUserBase):
    password: str


class AdminUser(AdminUserBase):
    id: int
    is_active: bool
    created_at: datetime
    
    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


# Stripe schemas
class CreateCheckoutRequest(BaseModel):
    email: EmailStr
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None


class CreateCheckoutResponse(BaseModel):
    checkout_url: str


# Dashboard schemas
class DashboardStats(BaseModel):
    total_users: int
    active_licenses: int
    active_subscriptions: int
    monthly_revenue: float


class LicenseListItem(BaseModel):
    id: int
    license_key: str
    user_email: str
    is_active: bool
    is_suspended: bool
    created_at: datetime
    last_validated: Optional[datetime]
    subscription_status: Optional[str]
    
    model_config = {"from_attributes": True}


# API Log schemas
class ApiLogEntry(BaseModel):
    id: int
    license_key_hash: Optional[str]
    endpoint: str
    method: str
    status_code: int
    ip_address: str
    timestamp: datetime
    
    model_config = {"from_attributes": True}
