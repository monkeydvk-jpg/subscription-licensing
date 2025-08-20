"""
General utility functions.
"""
import re
from datetime import datetime, timedelta
from typing import Optional


def format_currency(amount: float, currency: str = "USD") -> str:
    """Format amount as currency."""
    if currency.upper() == "USD":
        return f"${amount:.2f}"
    return f"{amount:.2f} {currency}"


def is_valid_email(email: str) -> bool:
    """Check if email format is valid."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def days_until_expiry(expires_at: Optional[datetime]) -> Optional[int]:
    """Calculate days until expiry."""
    if not expires_at:
        return None
    
    delta = expires_at - datetime.utcnow()
    return max(0, delta.days)


def format_datetime(dt: Optional[datetime]) -> str:
    """Format datetime for display."""
    if not dt:
        return "Never"
    
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def truncate_string(text: str, max_length: int = 50) -> str:
    """Truncate string with ellipsis."""
    if len(text) <= max_length:
        return text
    
    return text[:max_length - 3] + "..."


def get_subscription_status_display(status: str) -> str:
    """Get human-readable subscription status."""
    status_map = {
        "active": "Active",
        "past_due": "Past Due",
        "canceled": "Canceled",
        "unpaid": "Unpaid",
        "incomplete": "Incomplete",
        "incomplete_expired": "Incomplete Expired",
        "trialing": "Trialing",
        "ended": "Ended"
    }
    return status_map.get(status.lower(), status.title())


def calculate_next_billing_date(current_period_end: datetime) -> datetime:
    """Calculate next billing date (monthly)."""
    return current_period_end + timedelta(days=30)


def is_subscription_active(status: str) -> bool:
    """Check if subscription status is considered active."""
    active_statuses = {"active", "trialing"}
    return status.lower() in active_statuses
