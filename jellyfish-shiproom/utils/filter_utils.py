"""
Filter utility functions for the Jellyfish Status Report Generator.
This module handles the filtering and status determination of work items.
Note: The current implementation uses completion date and target date for status determination.
Future versions may use different criteria for status determination.
"""

from datetime import datetime, timedelta
from typing import List, Dict

# Status constants - these may be expanded or modified in future versions
STATUS_DONE = 'Done'
STATUS_IN_PROGRESS = 'In Progress'
STATUS_OVERDUE = 'Overdue'

def check_due_date_shift(date_history: List[Dict], seven_days_ago: datetime) -> bool:
    """
    Check if a due date was shifted by 2+ weeks in the last 7 days.
    
    Args:
        date_history: List of dicts containing due dates and their timestamps
        seven_days_ago: Datetime object representing 7 days ago
        
    Returns:
        True if due date was shifted by 2+ weeks in the last 7 days, False otherwise
    """
    if len(date_history) < 2:
        print(f"Not enough date history to check shift (need at least 2 dates, got {len(date_history)})")
        return False
        
    try:
        # Get the last two due dates
        previous_date = datetime.fromisoformat(date_history[-2]['date'].replace('Z', '+00:00'))
        current_date = datetime.fromisoformat(date_history[-1]['date'].replace('Z', '+00:00'))
        current_timestamp = date_history[-1]['timestamp']
        
        print(f"Checking due date shift:")
        print(f"  Previous date: {previous_date}")
        print(f"  Current date: {current_date}")
        print(f"  Current timestamp: {current_timestamp}")
        print(f"  Seven days ago: {seven_days_ago}")
        
        # Check if the change happened in the last 7 days
        if current_timestamp:
            # Convert timestamp to timezone-aware datetime
            change_date = datetime.fromisoformat(current_timestamp.replace('Z', '+00:00'))
            # Make seven_days_ago timezone-aware
            seven_days_ago = seven_days_ago.replace(tzinfo=change_date.tzinfo)
            
            if change_date >= seven_days_ago:
                # Calculate the shift in days
                shift_days = (current_date - previous_date).days
                print(f"  Shift days: {shift_days}")
                print(f"  Change was in last 7 days: True")
                print(f"  Shift >= 14 days: {shift_days >= 14}")
                return shift_days >= 14  # 2 weeks = 14 days
            else:
                print(f"  Change was in last 7 days: False (change date: {change_date})")
        else:
            print(f"  No timestamp available for the change")
            
    except Exception as e:
        print(f"Error checking due date shift: {e}")
        
    return False

def filter_items(items: List[Dict], seven_days_ago: datetime, today: datetime) -> List[Dict]:
    """
    Filter and determine status for work items based on completion and target dates.
    
    Current criteria:
    - Done: Completed in the last 7 days
    - Overdue: Past target date OR due date shifted by 2+ weeks in last 7 days
    - In Progress: All other cases
    
    Args:
        items: List of work items (deliverables or epics)
        seven_days_ago: Datetime object representing 7 days ago
        today: Current datetime
        
    Returns:
        List of items with added _status field
    """
    filtered = []
    
    for item in items:
        completed_date_str = item.get('completed_date')
        target_date_str = item.get('target_date')
        issue_key = item.get('source_issue_key', 'unknown')
        date_history = item.get('date_history', [])
        
        print(f"\nProcessing item {issue_key}:")
        print(f"  Target date: {target_date_str}")
        print(f"  Date history: {date_history}")
        
        # Check if completed in the last week
        if completed_date_str:
            try:
                completed_date = datetime.fromisoformat(completed_date_str.replace('Z', '+00:00'))
                if completed_date >= seven_days_ago:
                    # Completed this week
                    item['_status'] = STATUS_DONE
                    filtered.append(item)
                    print(f"  Status: Done (completed on {completed_date_str})")
                    continue
            except Exception as e:
                print(f"Error parsing completed_date for {issue_key}: {e}")
        
        # Check if overdue (past target date) or had a significant due date shift
        is_overdue = False
        if target_date_str:
            try:
                target_date = datetime.fromisoformat(target_date_str.replace('Z', '+00:00'))
                print(f"  Target date parsed: {target_date}")
                print(f"  Today: {today}")
                if target_date < today:
                    is_overdue = True
                    print(f"  Is overdue: True (target date is in the past)")
                else:
                    print(f"  Is overdue: False (target date is in the future)")
            except Exception as e:
                print(f"Error parsing target_date for {issue_key}: {e}")
        
        # Check for significant due date shift
        has_significant_shift = check_due_date_shift(date_history, seven_days_ago)
        print(f"  Has significant shift: {has_significant_shift}")
        
        if is_overdue or has_significant_shift:
            item['_status'] = STATUS_OVERDUE
            filtered.append(item)
            if is_overdue:
                print(f"  Final status: Overdue (past target date)")
            else:
                print(f"  Final status: Overdue (due date shifted by 2+ weeks)")
            continue
        
        # Otherwise it's in progress
        item['_status'] = STATUS_IN_PROGRESS
        filtered.append(item)
        print(f"  Final status: In Progress")
    
    return filtered 