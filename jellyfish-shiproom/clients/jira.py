"""
Jira client for interacting with Jira API
"""

import os
from typing import List, Dict
from jira import JIRA

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
                basic_auth=(self.jira_email, self.jira_token)
            )
            print(f"Initialized Jira client for {self.jira_url}")
        else:
            print("Warning: Jira credentials not configured. Due date history will not be available.")
            self.jira = None
    
    def get_due_date_history(self, issue_key: str) -> List[Dict]:
        """
        Get the history of due date changes for an issue in chronological order.
        Only includes the last change per day to filter out accidental/temporary changes.
        
        Handles the case where an item is created with an initial due date and then
        that date gets changed multiple times on the same day.
        
        Returns:
            List of dicts containing:
            - date: The due date string
            - timestamp: When the change was made
        """
        if not self.jira:
            return []
        
        try:
            # Get issue with changelog
            issue = self.jira.issue(issue_key, expand='changelog')
            
            # Get current due date
            current_due = getattr(issue.fields, 'duedate', None)
            
            # Collect all due date changes with timestamps
            changes = []
            for history in issue.changelog.histories:
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

            # Always include the original due date from the first change's "from" value (if it exists)
            due_dates = []
            if changes and changes[0]['from']:
                due_dates.append({
                    'date': changes[0]['from'],
                    'timestamp': changes[0]['timestamp']
                })

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

            # Remove duplicates by timestamp (shouldn't be needed, but for safety)
            seen_timestamps = set()
            unique_due_dates = []
            for due_date in due_dates:
                if due_date['timestamp'] not in seen_timestamps:
                    seen_timestamps.add(due_date['timestamp'])
                    unique_due_dates.append(due_date)
            due_dates = unique_due_dates

            # If we have a current due date that's not in our history, add it
            if current_due and not any(d['date'] == current_due for d in due_dates):
                due_dates.append({
                    'date': current_due,
                    'timestamp': changes[-1]['timestamp'] if changes else None
                })
            
            return due_dates
            
        except Exception as e:
            print(f"Error getting history for {issue_key}: {e}")
            return [] 