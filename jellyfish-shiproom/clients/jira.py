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
    
    def get_due_date_history(self, issue_key: str) -> List[str]:
        """Get the history of due date changes for an issue in chronological order"""
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
            
            # Build the chronological list of due dates
            due_dates = []
            
            if changes:
                # Start with the "from" value of the first change (if it exists)
                if changes[0]['from']:
                    due_dates.append(changes[0]['from'])
                
                # Add all the "to" values except the last one
                for change in changes[:-1]:
                    if change['to']:
                        due_dates.append(change['to'])
                
                # The current due date should be the last one (not struck through)
                if current_due:
                    due_dates.append(current_due)
                elif changes[-1]['to']:
                    # If no current due date, use the last "to" value
                    due_dates.append(changes[-1]['to'])
            else:
                # No changes found, just use current due date if it exists
                if current_due:
                    due_dates.append(current_due)
            
            return due_dates
            
        except Exception as e:
            print(f"Error getting history for {issue_key}: {e}")
            return [] 