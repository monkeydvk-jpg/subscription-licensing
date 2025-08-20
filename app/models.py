"""
SQLAlchemy models for users, licenses, and subscriptions.
"""
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import Boolean, Column, Integer, String, DateTime, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship

from .database import Base


class SubscriptionStatus(PyEnum):
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    UNPAID = "unpaid"
    INCOMPLETE = "incomplete"
    INCOMPLETE_EXPIRED = "incomplete_expired"
    TRIALING = "trialing"
    ENDED = "ended"


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    stripe_customer_id = Column(String(255), unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    licenses = relationship("License", back_populates="user")
    subscriptions = relationship("Subscription", back_populates="user")


class License(Base):
    __tablename__ = "licenses"
    
    id = Column(Integer, primary_key=True, index=True)
    license_key = Column(String(255), unique=True, index=True, nullable=False)
    license_key_hash = Column(String(255), unique=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # License status
    is_active = Column(Boolean, default=True)
    is_suspended = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    last_validated = Column(DateTime)
    expires_at = Column(DateTime)
    
    # Metadata
    extension_version = Column(String(50))
    device_fingerprint = Column(String(255))
    last_ip = Column(String(45))
    validation_count = Column(Integer, default=0)
    
    # Relationships
    user = relationship("User", back_populates="licenses")


class Subscription(Base):
    __tablename__ = "subscriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    stripe_subscription_id = Column(String(255), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Subscription details
    status = Column(Enum(SubscriptionStatus), nullable=False)
    current_period_start = Column(DateTime)
    current_period_end = Column(DateTime)
    end_time = Column(DateTime)  # Explicit subscription end time
    cancel_at_period_end = Column(Boolean, default=False)
    
    # Plan information
    stripe_price_id = Column(String(255))
    plan_name = Column(String(100))  # e.g., "Basic", "Pro", "Premium"
    billing_cycle = Column(String(20))  # e.g., "monthly", "yearly"
    trial_end = Column(DateTime)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="subscriptions")


class AdminUser(Base):
    __tablename__ = "admin_users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ApiLog(Base):
    __tablename__ = "api_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    license_key_hash = Column(String(255), index=True)
    endpoint = Column(String(255))
    method = Column(String(10))
    status_code = Column(Integer)
    ip_address = Column(String(45))
    user_agent = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)
