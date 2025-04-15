"""Extension to DateShift model to support weekly date tracking."""

from typing import List, Tuple, Dict, Optional
from datetime import datetime, timedelta, timezone
import logging

logger = logging.getLogger(__name__)

def ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Ensure a datetime is UTC timezone-aware."""
    if dt is None:
        return None
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt

def get_next_friday(date: datetime) -> datetime:
    """Get the next Friday (or same day if it's already Friday)."""
    # Ensure the date is timezone-aware
    date = ensure_utc(date)
    
    # Python: Monday is 0, Sunday is 6, so Friday is 4
    days_until_friday = (4 - date.weekday()) % 7
    if days_until_friday == 0:  # It's already Friday
        return date.replace(hour=0, minute=0, second=0, microsecond=0)
    next_friday = date + timedelta(days=days_until_friday)
    return next_friday.replace(hour=0, minute=0, second=0, microsecond=0)

def get_weekly_due_dates(date_changes: List[Tuple[datetime, datetime]], 
                        start_date: datetime, 
                        end_date: Optional[datetime] = None) -> List[Tuple[datetime, datetime]]:
    """
    Convert a list of date changes to regular weekly snapshots.
    
    Args:
        date_changes: List of (change_date, shift_date) tuples
        start_date: The start date of the issue
        end_date: The end date of the issue (optional)
    
    Returns:
        List of (friday_date, current_due_date) tuples, one for each Friday
    """
    if not date_changes:
        logger.warning("No date changes provided for weekly snapshot generation")
        return []
    
    # Ensure all dates are timezone-aware
    date_changes = [(ensure_utc(change_date), ensure_utc(shift_date)) 
                    for change_date, shift_date in date_changes]
    start_date = ensure_utc(start_date)
    end_date = ensure_utc(end_date) if end_date else None
    
    # Sort date changes by change date to ensure chronological order
    date_changes.sort(key=lambda x: x[0])
    
    # THE KEY FIX: Start from the project's start date, not from the first due date
    # Find the first Friday on or after the START DATE
    first_friday = get_next_friday(start_date)
    
    # Determine the last date to track
    now = datetime.now(timezone.utc)
    
    if end_date:
        # If resolved, use the resolution date
        last_date = end_date
    else:
        # If not resolved yet, use today's date
        last_date = now
    
    # Get the Friday on or after the last date
    last_friday = get_next_friday(last_date)
    
    logger.info(f"Generating weekly snapshots from {first_friday.strftime('%Y-%m-%d')} to {last_friday.strftime('%Y-%m-%d')}")
    
    # Initialize our weekly snapshots
    weekly_snapshots = []
    
    # Walk through each Friday from the first to the last
    current_friday = first_friday
    
    while current_friday <= last_friday:
        # Find the most recent change that happened before or on this Friday
        applicable_changes = [
            (change_date, due_date) for change_date, due_date in date_changes
            if change_date <= current_friday
        ]
        
        if applicable_changes:
            # Get the most recent change before this Friday
            latest_change = max(applicable_changes, key=lambda x: x[0])
            _, current_due_date = latest_change
            
            # Add this Friday's snapshot
            weekly_snapshots.append((current_friday, current_due_date))
        
        # Move to next Friday
        current_friday += timedelta(days=7)
    
    logger.info(f"Generated {len(weekly_snapshots)} weekly snapshots")
    
    return weekly_snapshots