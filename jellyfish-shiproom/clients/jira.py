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
            
            # Build the chronological list of due dates with timestamps
            due_dates = []
            
            if changes:
                # Start with the "from" value of the first change (if it exists)
                if changes[0]['from']:
                    due_dates.append({
                        'date': changes[0]['from'],
                        'timestamp': changes[0]['timestamp']
                    })
                
                # Add all the "to" values except the last one
                for change in changes[:-1]:
                    if change['to']:
                        due_dates.append({
                            'date': change['to'],
                            'timestamp': change['timestamp']
                        })
                
                # The current due date should be the last one (not struck through)
                if current_due:
                    due_dates.append({
                        'date': current_due,
                        'timestamp': changes[-1]['timestamp'] if changes else None
                    })
                elif changes[-1]['to']:
                    # If no current due date, use the last "to" value
                    due_dates.append({
                        'date': changes[-1]['to'],
                        'timestamp': changes[-1]['timestamp']
                    })
            else:
                # No changes found, just use current due date if it exists
                if current_due:
                    due_dates.append({
                        'date': current_due,
                        'timestamp': None
                    })
            
            return due_dates
            
        except Exception as e:
            print(f"Error getting history for {issue_key}: {e}")
            return [] 