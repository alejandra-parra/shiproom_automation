"""
Jira client for interacting with Jira API
"""

import os
from typing import List, Dict
from jira import JIRA

class JiraClient:
    """Client for interacting with Jira API"""
    
    def __init__(self, config: Dict):
        # Get Jira credentials from environment variables only
        jira_url = os.getenv('JIRA_URL')
        jira_email = os.getenv('JIRA_EMAIL')
        jira_token = os.getenv('JIRA_TOKEN')
        
        if not all([jira_url, jira_email, jira_token]):
            raise ValueError("JIRA_URL, JIRA_EMAIL, and JIRA_TOKEN environment variables must be set")
        
        self.client = JIRA(
            server=jira_url,
            basic_auth=(jira_email, jira_token)
        )
        print(f"Initialized Jira client with URL: {jira_url}")
    
    def get_due_date_history(self, issue_key: str) -> List[str]:
        """Get the history of due date changes for an issue"""
        try:
            issue = self.client.issue(issue_key, expand='changelog')
            due_date_history = []
            
            for history in issue.changelog.histories:
                for item in history.items:
                    if item.field == 'duedate':
                        due_date_history.append(item.toString)
            
            return due_date_history
            
        except Exception as e:
            print(f"Error getting due date history for {issue_key}: {e}")
            return [] 