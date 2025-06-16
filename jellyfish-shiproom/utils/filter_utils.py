"""
Filter utility functions for the Jellyfish Status Report Generator.
This module handles the filtering and status determination of work items.
Note: The current implementation uses completion date and target date for status determination.
Future versions may use different criteria for status determination.
"""

from datetime import datetime, timedelta
from typing import List, Dict
from utils.date_utils import get_weekly_lookback_range

# Status constants - these may be expanded or modified in future versions
STATUS_DONE = 'Done'
STATUS_IN_PROGRESS = 'In Progress'
STATUS_OVERDUE = 'Overdue'

def check_due_date_shift(date_history: List[Dict], lookback_start: datetime) -> bool:
    """
    Check if a due date was shifted by 2+ weeks in the lookback period.
    
    Args:
        date_history: List of dicts containing due dates and their timestamps
        lookback_start: Datetime object representing the start of the lookback period
        
    Returns:
        True if due date was shifted by 2+ weeks in the lookback period, False otherwise
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
        print(f"  Lookback start: {lookback_start}")
        
        # Check if the change happened in the lookback period
        if current_timestamp:
            # Convert timestamp to timezone-aware datetime
            change_date = datetime.fromisoformat(current_timestamp.replace('Z', '+00:00'))
            # Make lookback_start timezone-aware
            lookback_start = lookback_start.replace(tzinfo=change_date.tzinfo)
            
            if change_date >= lookback_start:
                # Calculate the shift in days
                shift_days = (current_date - previous_date).days
                print(f"  Shift days: {shift_days}")
                print(f"  Change was in lookback period: True")
                print(f"  Shift >= 14 days: {shift_days >= 14}")
                return shift_days >= 14  # 2 weeks = 14 days
            else:
                print(f"  Change was in lookback period: False (change date: {change_date})")
        else:
            print(f"  No timestamp available for the change")
            
    except Exception as e:
        print(f"Error checking due date shift: {e}")
        
    return False

def filter_items(items: List[Dict], lookback_start: datetime, lookback_end: datetime) -> List[Dict]:
    """
    Filter and determine status for work items based on completion and target dates.
    
    Current criteria:
    - Done: Completed in the lookback period
    - Overdue: Past target date OR due date shifted by 2+ weeks in lookback period
    - In Progress: All other cases
    
    Only includes items that are either:
    - "In Progress" (based on source_issue_status)
    - Completed in the lookback period
    AND
    - Have "Roadmap" in their investment_classification
    
    Args:
        items: List of work items (deliverables or epics)
        lookback_start: Datetime object representing the start of the lookback period
        lookback_end: Datetime object representing the end of the lookback period
        
    Returns:
        List of items with added _status field
    """
    filtered = []
    
    for item in items:
        completed_date_str = item.get('completed_date')
        target_date_str = item.get('target_date')
        issue_key = item.get('source_issue_key', 'unknown')
        date_history = item.get('date_history', [])
        source_status = item.get('source_issue_status', '')
        investment_classification = item.get('investment_classification', '')
        
        print(f"\nProcessing item {issue_key}:")
        print(f"  Target date: {target_date_str}")
        print(f"  Date history: {date_history}")
        print(f"  Source status: {source_status}")
        print(f"  Investment classification: {investment_classification}")
        
        # Skip items that don't have "Roadmap" in their investment classification
        if "Roadmap" not in investment_classification:
            print(f"  Skipping item (not a roadmap item)")
            continue
        
        # Check if completed in the lookback period
        if completed_date_str:
            try:
                completed_date = datetime.fromisoformat(completed_date_str.replace('Z', '+00:00'))
                if lookback_start <= completed_date <= lookback_end:
                    # Completed in lookback period
                    item['_status'] = STATUS_DONE
                    filtered.append(item)
                    print(f"  Status: Done (completed on {completed_date_str})")
                    continue
            except Exception as e:
                print(f"Error parsing completed_date for {issue_key}: {e}")
        
        # Skip items that are not "In Progress"
        if source_status != "In Progress":
            print(f"  Skipping item (not in progress)")
            continue
        
        # Check if overdue (past target date) or had a significant due date shift
        is_overdue = False
        if target_date_str:
            try:
                target_date = datetime.fromisoformat(target_date_str.replace('Z', '+00:00'))
                print(f"  Target date parsed: {target_date}")
                print(f"  Lookback end: {lookback_end}")
                if target_date < lookback_end:
                    is_overdue = True
                    print(f"  Is overdue: True (target date is in the past)")
                else:
                    print(f"  Is overdue: False (target date is in the future)")
            except Exception as e:
                print(f"Error parsing target_date for {issue_key}: {e}")
        
        # Check for significant due date shift
        has_significant_shift = check_due_date_shift(date_history, lookback_start)
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