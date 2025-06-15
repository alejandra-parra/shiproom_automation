"""
Date utility functions for the Jellyfish Status Report Generator
"""

from datetime import datetime

def format_date(date_str: str) -> str:
    """Format a date string to a more readable format"""
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        return date_obj.strftime('%b %d, %Y')
    except Exception:
        return date_str 