"""
Date utility functions for the Jellyfish Status Report Generator.
"""

from datetime import datetime, timedelta
from typing import Tuple

def get_friday_of_week(date: datetime) -> datetime:
    """
    Get the Friday of the week containing the given date.
    If the date is already a Friday, return that date.
    
    Args:
        date (datetime): The date to find the Friday for
        
    Returns:
        datetime: The Friday of that week
    """
    # Get the day of the week (0 is Monday, 4 is Friday, 6 is Sunday)
    days_since_monday = date.weekday()
    # Calculate days until Friday (4 is Friday)
    days_until_friday = (4 - days_since_monday) % 7
    # If days_until_friday is 0, we're already on Friday
    if days_until_friday == 0:
        return date
    # Otherwise, add the remaining days to get to Friday
    return date + timedelta(days=days_until_friday)

def get_report_date_range() -> Tuple[datetime, datetime]:
    """
    Get the date range for the report (21 days before today until today).
    The 7-day lookback window is based on the Friday of the completed week.
    
    Returns:
        Tuple[datetime, datetime]: A tuple containing (start_date, end_date)
    """
    today = datetime.now()
    start_date = today - timedelta(days=21)
    return start_date, today

def get_weekly_lookback_range(end_date: datetime) -> Tuple[datetime, datetime]:
    """
    Get the 7-day lookback range based on the Friday of the completed week.
    
    Args:
        end_date (datetime): The end date of the completed week
        
    Returns:
        Tuple[datetime, datetime]: A tuple containing (start_date, end_date) for the 7-day lookback
    """
    # Get the Friday of the completed week
    friday = get_friday_of_week(end_date)
    # The start date is 7 days before the Friday
    start_date = friday - timedelta(days=7)
    return start_date, friday

def format_date(date_str: str) -> str:
    """
    Format a date string from ISO format to YYYY-MM-DD format.
    
    Args:
        date_str (str): Date string in ISO format (e.g., "2025-06-15T00:00:00Z")
        
    Returns:
        str: Formatted date string (e.g., "2025-06-15") or empty string if invalid
    """
    if not date_str:
        return ""
    
    try:
        # Handle both Z and +00:00 timezone formats
        date_str = date_str.replace('Z', '+00:00')
        date = datetime.fromisoformat(date_str)
        return date.strftime("%Y-%m-%d")
    except Exception as e:
        print(f"Error formatting date {date_str}: {e}")
        return "" 