"""Utility functions for the Jira Due Date Analysis tool."""

from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

def parse_jira_datetime(date_str: str | None, context: str = "") -> datetime:
    """Parse a Jira datetime string into a timezone-aware datetime object."""
    # if not date_str:
    #     current_time = datetime.now(timezone.utc)
    #     logger.warning(f"No date provided{' for ' + context if context else ''}, using current time: {current_time}")
    #     return current_time
    if not date_str:
       return None
    
    # Try parsing with timezone
    try:
        return datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S.%f%z')
    except ValueError:
        pass

    # Try parsing without timezone but with time
    try:
        dt = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S.%f')
        utc_dt = dt.replace(tzinfo=timezone.utc)  # Convert to UTC timezone
        logger.debug(f"Converted timezone-naive datetime to UTC{' for ' + context if context else ''}: {date_str} -> {utc_dt}")
        return utc_dt
    except ValueError:
        pass

    # Try parsing date-only format
    try:
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        utc_dt = dt.replace(tzinfo=timezone.utc)  # Convert to UTC
        logger.debug(f"Converted timezone-naive date to UTC{' for ' + context if context else ''}: {date_str} -> {utc_dt}")
        return utc_dt
    except ValueError:
        pass

    # If all parsing attempts fail, fallback to current UTC time
    current_time = datetime.now(timezone.utc)
    logger.warning(
        f"Failed to parse date string{' for ' + context if context else ''}: '{date_str}', "
        f"using current time: {current_time}"
    )
    return current_time

def validate_date_range(start_date: str, end_date: str) -> bool:
    """Validate that the start date is before the end date."""
    start = parse_jira_datetime(start_date, "range start")
    end = parse_jira_datetime(end_date, "range end")
    return start < end

def format_duration(days: int) -> str:
    """Format a duration in days into a human-readable string."""
    if days < 30:
        return f"{days} days"
    months = days // 30
    remaining_days = days % 30
    if remaining_days == 0:
        return f"{months} months"
    return f"{months} months, {remaining_days} days"