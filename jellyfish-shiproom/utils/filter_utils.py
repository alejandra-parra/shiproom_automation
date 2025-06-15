"""
Filter utility functions for the Jellyfish Status Report Generator.
This module handles the filtering and status determination of work items.
Note: The current implementation uses completion date and target date for status determination.
Future versions may use different criteria for status determination.
"""

from datetime import datetime
from typing import List, Dict

# Status constants - these may be expanded or modified in future versions
STATUS_DONE = 'Done'
STATUS_IN_PROGRESS = 'In Progress'
STATUS_OVERDUE = 'Overdue'

def filter_items(items: List[Dict], seven_days_ago: datetime, today: datetime) -> List[Dict]:
    """
    Filter and determine status for work items based on completion and target dates.
    
    Current criteria:
    - Done: Completed in the last 7 days
    - Overdue: Past target date
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
        
        # Check if completed in the last week
        if completed_date_str:
            try:
                completed_date = datetime.fromisoformat(completed_date_str.replace('Z', '+00:00'))
                if completed_date >= seven_days_ago:
                    # Completed this week
                    item['_status'] = STATUS_DONE
                    filtered.append(item)
                    print(f"{issue_key}: Completed on {completed_date_str} - Done")
                    continue
            except Exception as e:
                print(f"Error parsing completed_date for {issue_key}: {e}")
        
        # Check if overdue (past target date)
        if target_date_str:
            try:
                target_date = datetime.fromisoformat(target_date_str.replace('Z', '+00:00'))
                if target_date < today:
                    # Past target date
                    item['_status'] = STATUS_OVERDUE
                    filtered.append(item)
                    print(f"{issue_key}: Overdue (target: {target_date_str}) - Overdue")
                    continue
            except Exception as e:
                print(f"Error parsing target_date for {issue_key}: {e}")
        
        # Otherwise it's in progress
        item['_status'] = STATUS_IN_PROGRESS
        filtered.append(item)
    
    return filtered 