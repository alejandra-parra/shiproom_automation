"""
Filter utility functions for the Jellyfish Status Report Generator.
This module handles the filtering and status determination of work items.
Note: The current implementation uses completion date and target date for status determination.
Future versions may use different criteria for status determination.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Tuple
from utils.date_utils import get_weekly_lookback_range
import json
import os

# Status constants - these may be expanded or modified in future versions
STATUS_DONE = 'Done'
STATUS_IN_PROGRESS = 'In Progress'
STATUS_OVERDUE = 'Overdue'

def save_excluded_items(excluded_items: List[Dict], output_dir: str = "logs"):
    """
    Save excluded items to a JSON file with timestamp.
    
    Args:
        excluded_items: List of excluded items with their reasons
        output_dir: Directory to save the log file
    """
    # Create logs directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Create filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(output_dir, f"excluded_items_{timestamp}.json")
    
    # Save to file
    with open(filename, 'w') as f:
        json.dump(excluded_items, f, indent=2)
    
    print(f"\nExcluded items saved to: {filename}")

def format_excluded_items_for_display(excluded_items: List[Dict]) -> str:
    """
    Format excluded items into a readable string for display in slides.
    
    Args:
        excluded_items: List of excluded items with their reasons
        
    Returns:
        Formatted string with one item per line
    """
    if not excluded_items:
        return "No items were excluded."
    
    formatted_lines = []
    for item in excluded_items:
        issue_key = item.get('issue_key', 'Unknown')
        name = item.get('name', 'Unknown')
        status = item.get('status', 'Unknown')
        investment_classification = item.get('investment_classification', 'Unknown')
        exclusion_reason = item.get('exclusion_reason', 'Unknown reason')
        
        # Format: DX-60 - MCP Server POC (Roadmap, Done) : Not in progress or in review (status: Done)
        formatted_line = f"{issue_key} - {name} ({investment_classification}, {status}) : {exclusion_reason}"
        formatted_lines.append(formatted_line)
    
    return "\n".join(formatted_lines)

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

def filter_items(items: List[Dict], lookback_start: datetime, lookback_end: datetime) -> Tuple[List[Dict], List[Dict]]:
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
        Tuple of (filtered_items, excluded_items) where filtered_items have added _status field
    """
    filtered = []
    excluded_items = []
    
    for item in items:
        issue_key = item.get('source_issue_key', 'unknown')
        name = item.get('name', '')
        source_status = item.get('source_issue_status', '')
        investment_classification = item.get('investment_classification', '')
        completed_date_str = item.get('completed_date')
        target_date_str = item.get('target_date')
        date_history = item.get('date_history', [])
        
        print(f"\nProcessing item {issue_key}:")
        print(f"  Target date: {target_date_str}")
        print(f"  Date history: {date_history}")
        print(f"  Source status: {source_status}")
        print(f"  Investment classification: {investment_classification}")
        
        # Skip items that don't have "Roadmap" in their investment classification
        if "Roadmap" not in investment_classification:
            print(f"  Skipping item (not a roadmap item)")
            excluded_items.append({
                'issue_key': issue_key,
                'name': name,
                'status': source_status,
                'investment_classification': investment_classification,
                'exclusion_reason': 'Not a roadmap item'
            })
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
        
        # Skip items that are not "In Progress", "In Review", or completed in lookback period
        if source_status not in ["In Progress", "In Review"]:
            print(f"  Skipping item (not in progress or in review)")
            excluded_items.append({
                'issue_key': issue_key,
                'name': name,
                'status': source_status,
                'investment_classification': investment_classification,
                'exclusion_reason': f'Not in progress or in review (status: {source_status})'
            })
            continue
        
        # Check if overdue (2+ weeks past target date) or had a significant due date shift
        is_overdue = False
        
        # First check target_date_str if available
        if target_date_str:
            try:
                target_date = datetime.fromisoformat(target_date_str.replace('Z', '+00:00'))
                print(f"  Target date parsed: {target_date}")
                print(f"  Lookback end: {lookback_end}")
                # Check if target date is 2+ weeks in the past
                two_weeks_ago = lookback_end - timedelta(days=14)
                if target_date < two_weeks_ago:
                    is_overdue = True
                    print(f"  Is overdue: True (target date is 2+ weeks in the past)")
                else:
                    print(f"  Is overdue: False (target date is not 2+ weeks in the past)")
            except Exception as e:
                print(f"Error parsing target_date for {issue_key}: {e}")
        
        # If no target_date_str or not overdue, check the most recent due date from date_history
        if not is_overdue and date_history:
            try:
                # Get the most recent due date from date history
                latest_due_date_str = date_history[-1]['date']
                latest_due_date = datetime.fromisoformat(latest_due_date_str.replace('Z', '+00:00'))
                print(f"  Latest due date from history: {latest_due_date}")
                print(f"  Lookback end: {lookback_end}")
                # Check if latest due date is 2+ weeks in the past
                two_weeks_ago = lookback_end - timedelta(days=14)
                if latest_due_date < two_weeks_ago:
                    is_overdue = True
                    print(f"  Is overdue: True (latest due date from history is 2+ weeks in the past)")
                else:
                    print(f"  Is overdue: False (latest due date from history is not 2+ weeks in the past)")
            except Exception as e:
                print(f"Error parsing latest due date from history for {issue_key}: {e}")
        
        # If still not overdue, check for any other due date fields that might exist
        if not is_overdue:
            # Check for other potential due date fields in the item
            due_date_fields = ['due_date', 'duedate', 'dueDate', 'targetDate', 'target_date']
            for field in due_date_fields:
                if field in item and item[field]:
                    try:
                        due_date_str = str(item[field])
                        due_date = datetime.fromisoformat(due_date_str.replace('Z', '+00:00'))
                        print(f"  Found due date in field '{field}': {due_date}")
                        print(f"  Lookback end: {lookback_end}")
                        # Check if due date is 2+ weeks in the past
                        two_weeks_ago = lookback_end - timedelta(days=14)
                        if due_date < two_weeks_ago:
                            is_overdue = True
                            print(f"  Is overdue: True (due date from field '{field}' is 2+ weeks in the past)")
                            break
                        else:
                            print(f"  Is overdue: False (due date from field '{field}' is not 2+ weeks in the past)")
                    except Exception as e:
                        print(f"Error parsing due date from field '{field}' for {issue_key}: {e}")
                        continue
        
        # Check for significant due date shift
        has_significant_shift = check_due_date_shift(date_history, lookback_start)
        print(f"  Has significant shift: {has_significant_shift}")
        
        if is_overdue or has_significant_shift:
            item['_status'] = STATUS_OVERDUE
            filtered.append(item)
            if is_overdue:
                print(f"  Final status: Overdue (2+ weeks past due date)")
            else:
                print(f"  Final status: Overdue (due date shifted by 2+ weeks)")
            continue
        
        # Otherwise it's in progress
        item['_status'] = STATUS_IN_PROGRESS
        filtered.append(item)
        print(f"  Final status: In Progress")
    
    # Save excluded items to file
    if excluded_items:
        save_excluded_items(excluded_items)
    
    return filtered, excluded_items 