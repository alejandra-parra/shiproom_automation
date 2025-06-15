"""
Date utility functions for the Jellyfish Status Report Generator.
"""

from datetime import datetime, timedelta
from typing import Tuple

def get_report_date_range() -> Tuple[datetime, datetime]:
    """
    Get the date range for the report (21 days before today until today).
    
    Returns:
        Tuple[datetime, datetime]: A tuple containing (start_date, end_date)
    """
    today = datetime.now()
    start_date = today - timedelta(days=21)
    return start_date, today

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