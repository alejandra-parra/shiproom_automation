"""
Jira client for interacting with Jira API
"""

import os
from typing import List, Dict
from jira import JIRA
import json

class JiraClient:
    """Client for interacting with Jira API to get issue history"""
    
    def __init__(self, config: Dict):
        # Get Jira credentials from environment variables only
        self.jira_url = os.getenv('JIRA_URL', '')
        self.jira_email = os.getenv('JIRA_EMAIL', '')
        self.jira_token = os.getenv('JIRA_API_TOKEN', '')
        
        if self.jira_url and self.jira_email and self.jira_token:
            self.jira = JIRA(
                server=self.jira_url,
                basic_auth=(self.jira_email, self.jira_token),
                timeout=30  # 30 second timeout
            )
            print(f"Initialized Jira client for {self.jira_url}")
        else:
            print("Warning: Jira credentials not configured. Due date history will not be available.")
            self.jira = None
    
    def get_issue_labels(self, issue_key: str) -> List[str]:
        """
        Get the labels for a Jira issue.
        
        Args:
            issue_key: The Jira issue key (e.g., 'PROJ-123')
            
        Returns:
            List of label strings, or empty list if error or no labels
        """
        if not self.jira:
            return []
        
        try:
            # Get issue with labels field
            issue = self.jira.issue(issue_key, fields='labels')
            labels = getattr(issue.fields, 'labels', [])
            return labels if labels else []
        except Exception as e:
            print(f"Error getting labels for {issue_key}: {e}")
            return []
    
    def get_due_date_history(self, issue_key: str) -> List[Dict]:
        """
        Get the history of due date changes for an issue in chronological order.
        Only includes the last change per day to filter out accidental/temporary changes.
        
        Handles the case where an item is created with an initial due date and then
        that date gets changed multiple times on the same day.
        
        Only includes due date changes that happened on or after the issue was moved to "In Progress" status,
        since early due dates are often just placeholder estimates made during planning.
        
        Returns:
            List of dicts containing:
            - date: The due date string
            - timestamp: When the change was made
        """
        if not self.jira:
            return []
        
        try:
            # Get current due date first (without changelog to be efficient)
            issue_basic = self.jira.issue(issue_key, fields='duedate')
            current_due = getattr(issue_basic.fields, 'duedate', None)
            
            # Collect all histories using pagination
            all_histories = []
            start_at = 0
            max_results = 100  # Jira's default pagination size
            max_pages = 10  # Safety limit to prevent infinite loops
            seen_history_ids = set()  # Track seen history IDs to detect duplicates
            
            page_count = 0
            while page_count < max_pages:
                # Get changelog with pagination
                issue_with_changelog = self.jira.issue(
                    issue_key, 
                    expand=f'changelog[{start_at}:{start_at + max_results}]'
                )
                
                # Check if we have any histories in this page
                if not hasattr(issue_with_changelog.changelog, 'histories') or not issue_with_changelog.changelog.histories:
                    break
                
                # Add histories from this page
                histories_in_page = len(issue_with_changelog.changelog.histories)
                
                # Check for duplicate data (same history IDs as before)
                current_history_ids = {h.id for h in issue_with_changelog.changelog.histories}
                if current_history_ids.issubset(seen_history_ids):
                    # We're getting duplicate data, so we've reached the end
                    break
                
                # Add new histories and track their IDs
                all_histories.extend(issue_with_changelog.changelog.histories)
                seen_history_ids.update(current_history_ids)
                
                # Check if we've reached the end (got fewer than max_results)
                if histories_in_page < max_results:
                    break
                
                start_at += max_results
                page_count += 1
            
            # Find when the issue was moved to "In Progress" status and what the due date was at that time
            in_progress_timestamp = None
            original_due_at_in_progress = None
            
            # Track the due date chronologically through the changelog
            current_tracked_due = None
            
            for history in sorted(all_histories, key=lambda x: x.created):
                for item in history.items:
                    if item.field.lower() in ['duedate', 'due date']:
                        # Update our tracked due date
                        current_tracked_due = item.toString
                    
                    elif item.field.lower() in ['status', 'statuscategorychangedate']:
                        # Check if this change moved the issue to "In Progress" or similar status
                        to_status = item.toString.lower() if item.toString else ""
                        if any(status in to_status for status in ['in progress', 'active', 'started']):
                            in_progress_timestamp = history.created
                            original_due_at_in_progress = current_tracked_due
                            break
                if in_progress_timestamp:
                    break
            
            # Collect all due date changes with timestamps
            changes = []
            for history in all_histories:
                created = history.created  # Timestamp of the change
                for item in history.items:
                    if item.field.lower() in ['duedate', 'due date']:
                        changes.append({
                            'timestamp': created,
                            'from': item.fromString,
                            'to': item.toString
                        })
            
            # Sort by timestamp (oldest first)
            changes.sort(key=lambda x: x['timestamp'])
            
            # Filter changes to only include those on or after "In Progress" timestamp
            if in_progress_timestamp:
                filtered_changes = []
                for change in changes:
                    # Include the change if it happened on or after the "In Progress" timestamp
                    if change['timestamp'] >= in_progress_timestamp:
                        filtered_changes.append(change)
                changes = filtered_changes
            
            # If no changes after "In Progress", just return current due date if it exists
            if not changes:
                if current_due:
                    return [{'date': current_due, 'timestamp': None}]
                return []
            
            # Build the chronological list of due dates with timestamps
            due_dates = []
            
            # Include the original due date that existed when moved to "In Progress" (if it exists)
            if original_due_at_in_progress:
                # Normalize for comparison to avoid duplicates
                original_normalized = original_due_at_in_progress.split(' ')[0] if ' ' in original_due_at_in_progress else original_due_at_in_progress
                current_normalized = current_due.split(' ')[0] if current_due and ' ' in current_due else current_due
                
                # Only include the original due date if it's different from the current due date
                if original_normalized != current_normalized:
                    due_dates.append({
                        'date': original_due_at_in_progress,
                        'timestamp': in_progress_timestamp
                    })
            
            # For changes after "In Progress", we only include the "to" values
            # (the new due dates that were set), not the "from" values
            # Group changes by day and keep only the last change per day
            daily_changes = {}
            for change in changes:
                date_key = change['timestamp'][:10]
                daily_changes[date_key] = change  # this will keep the last change for the day

            # For each day's last change, include the "to" value
            for change in sorted(daily_changes.values(), key=lambda x: x['timestamp']):
                if change['to']:
                    due_dates.append({
                        'date': change['to'],
                        'timestamp': change['timestamp']
                    })
            
            # If we have a current due date that's not in our history, add it
            if current_due:
                # Normalize current_due for comparison (remove time component if present)
                current_due_normalized = current_due.split(' ')[0] if ' ' in current_due else current_due
                
                # Check if this due date is already in our history (normalizing for comparison)
                already_in_history = False
                for d in due_dates:
                    d_date_normalized = d['date'].split(' ')[0] if ' ' in d['date'] else d['date']
                    if d_date_normalized == current_due_normalized:
                        already_in_history = True
                        break
                
                if not already_in_history:
                    due_dates.append({
                        'date': current_due,
                        'timestamp': changes[-1]['timestamp'] if changes else None
                    })
            
            return due_dates
            
        except Exception as e:
            print(f"Error getting history for {issue_key}: {e}")
            return [] 