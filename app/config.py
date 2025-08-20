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
        # Get ALL environment variables that might contain a PostgreSQL URL
        all_env_vars = list(os.environ.items())
        postgres_candidates = []
        
        # First, try explicit settings
        explicit_urls = [
            self.postgres_url,
            self.postgres_database_url, 
            self.neon_database_url,
            os.getenv('POSTGRES_URL'),
            os.getenv('POSTGRES_DATABASE_URL'),
            os.getenv('NEON_DATABASE_URL'),
            os.getenv('DATABASE_URL'),
        ]
        
        # Then scan ALL environment variables for PostgreSQL URLs
        for key, value in all_env_vars:
            if value and ('postgresql://' in value or 'postgres://' in value):
                postgres_candidates.append((key, value))
        
        # Debug: Print what we found
        print(f"🔍 Found {len(postgres_candidates)} PostgreSQL URL candidates:")
        for key, url in postgres_candidates:
            print(f"  {key}: {url[:50]}{'...' if len(url) > 50 else ''}")
        
        # Try explicit URLs first
        for url in explicit_urls:
            if url and ('postgresql://' in url or 'postgres://' in url):
                print(f"✅ Using explicit PostgreSQL URL: {url[:50]}...")
                return url
        
        # Then try any PostgreSQL URL we found
        if postgres_candidates:
            selected_key, selected_url = postgres_candidates[0]  # Use the first one found
            print(f"✅ Using found PostgreSQL URL from {selected_key}: {selected_url[:50]}...")
            return selected_url
                
        # Fallback to SQLite (for local development)
        print("⚠️ No PostgreSQL URL found, falling back to SQLite")
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
