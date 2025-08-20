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
    postgres_database_url: Optional[str] = None  # Alternative name
    neon_database_url: Optional[str] = None  # For Neon
    
    @property
    def effective_database_url(self) -> str:
        """Get the effective database URL, preferring PostgreSQL if available."""
        # Try multiple possible PostgreSQL environment variable names
        postgres_urls = [
            self.postgres_url,
            self.postgres_database_url, 
            self.neon_database_url,
            os.getenv('POSTGRES_URL'),
            os.getenv('POSTGRES_DATABASE_URL'),
            os.getenv('NEON_DATABASE_URL'),
            os.getenv('DATABASE_URL'),  # Some services use this for PostgreSQL
            # Vercel Postgres often creates variables with DATABASE_URL_ prefix
            os.getenv('DATABASE_URL_POSTGRES_URL'),
            os.getenv('DATABASE_URL_DATABASE_URL'),
            os.getenv('DATABASE_URL_POSTGRES_PRISMA_URL'),
            os.getenv('DATABASE_URL_POSTGRES_URL_NON_POOLING')
        ]
        
        # Debug: Print what we found
        for i, url in enumerate(postgres_urls):
            if url:
                var_names = [
                    'postgres_url', 'postgres_database_url', 'neon_database_url',
                    'POSTGRES_URL', 'POSTGRES_DATABASE_URL', 'NEON_DATABASE_URL', 'DATABASE_URL',
                    'DATABASE_URL_POSTGRES_URL', 'DATABASE_URL_DATABASE_URL', 'DATABASE_URL_POSTGRES_PRISMA_URL', 'DATABASE_URL_POSTGRES_URL_NON_POOLING'
                ]
                print(f"🔍 Found {var_names[i]}: {url[:50]}{'...' if len(url) > 50 else ''}")
        
        for url in postgres_urls:
            if url and ('postgresql://' in url or 'postgres://' in url):
                return url
                
        # Fallback to SQLite (for local development)
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
