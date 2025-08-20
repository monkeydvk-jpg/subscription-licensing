"""
Configuration settings for the subscription licensing system.
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite:///./subscriptions.db"
    postgres_url: Optional[str] = None  # For Vercel Postgres
    
    @property
    def effective_database_url(self) -> str:
        """Get the effective database URL, preferring PostgreSQL if available."""
        if self.postgres_url:
            return self.postgres_url
        return self.database_url
    
    # Security
    secret_key: str = "your-secret-key-change-this-in-production"
    access_token_expire_minutes: int = 30
    admin_username: str = "admin"
    admin_password: str = "changeme"
    
    # Stripe
    stripe_publishable_key: str = ""
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_id: str = ""  # Monthly subscription price ID
    
    # Application
    app_name: str = "Extension License Manager"
    app_version: str = "1.0.0"
    
    # License settings
    license_key_length: int = 32
    license_check_interval_hours: int = 24
    
    # URLs
    success_url: str = "http://localhost:8000/success"
    cancel_url: str = "http://localhost:8000/cancel"
    
    model_config = {"env_file": ".env"}


settings = Settings()
