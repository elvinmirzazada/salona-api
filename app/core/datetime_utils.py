"""
Utility module for UTC datetime handling across the application.
All datetime operations should use UTC timezone for consistency.
"""
from datetime import datetime, timezone
from typing import Optional


def utcnow() -> datetime:
    """
    Get current UTC datetime (timezone-aware).
    
    Returns:
        datetime: Current UTC time with timezone info
    """
    return datetime.now(timezone.utc)


def ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """
    Ensure a datetime is timezone-aware (UTC).
    If it's naive, assume it's UTC and make it aware.
    If it has a different timezone, convert to UTC.
    
    Args:
        dt: Input datetime (can be naive or timezone-aware)
        
    Returns:
        datetime: Timezone-aware datetime in UTC, or None if input is None
    """
    if dt is None:
        return None
    
    if dt.tzinfo is None:
        # Naive datetime - assume UTC
        return dt.replace(tzinfo=timezone.utc)
    
    # Already timezone-aware - convert to UTC if needed
    return dt.astimezone(timezone.utc)


def make_naive_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """
    Convert a timezone-aware datetime to naive UTC datetime.
    Useful for database operations that expect naive datetimes.
    
    Args:
        dt: Input datetime
        
    Returns:
        datetime: Naive datetime in UTC, or None if input is None
    """
    if dt is None:
        return None
    
    if dt.tzinfo is None:
        # Already naive
        return dt
    
    # Convert to UTC and remove timezone info
    return dt.astimezone(timezone.utc).replace(tzinfo=None)

