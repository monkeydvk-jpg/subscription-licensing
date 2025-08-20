"""
Security utilities for password hashing, JWT tokens, and license key management.
"""
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional
from passlib.context import CryptContext
from jose import JWTError, jwt

from .config import settings

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
ALGORITHM = "HS256"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate hash for a password."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Optional[str]:
    """Verify JWT token and return username."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
        return username
    except JWTError:
        return None


def generate_license_key(length: Optional[int] = None) -> str:
    """Generate a secure random license key."""
    if length is None:
        length = settings.license_key_length
    
    # Use URL-safe base64 characters (A-Z, a-z, 0-9, -, _)
    return secrets.token_urlsafe(length)[:length]


def hash_license_key(license_key: str) -> str:
    """Create a hash of the license key for secure storage."""
    return hashlib.sha256(license_key.encode()).hexdigest()


def verify_license_key(license_key: str, license_key_hash: str) -> bool:
    """Verify a license key against its hash."""
    return hash_license_key(license_key) == license_key_hash


def generate_device_fingerprint(user_agent: str, additional_data: Optional[str] = None) -> str:
    """Generate a device fingerprint from user agent and additional data."""
    data = user_agent
    if additional_data:
        data += additional_data
    
    return hashlib.md5(data.encode()).hexdigest()[:16]


def is_license_key_format_valid(license_key: str) -> bool:
    """Check if license key format is valid."""
    if not license_key:
        return False
    
    # Check length
    if len(license_key) != settings.license_key_length:
        return False
    
    # Check characters (URL-safe base64)
    allowed_chars = set('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_')
    return all(c in allowed_chars for c in license_key)


def mask_license_key(license_key: str, show_chars: int = 4) -> str:
    """Mask license key for display purposes."""
    if len(license_key) <= show_chars * 2:
        return license_key
    
    return f"{license_key[:show_chars]}{'*' * (len(license_key) - show_chars * 2)}{license_key[-show_chars:]}"
