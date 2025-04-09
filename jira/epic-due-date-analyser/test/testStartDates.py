from jira import JIRA
from datetime import datetime
import sys
from dotenv import load_dotenv
import os

class JiraDateAnalyzer:
    def __init__(self):
        load_dotenv()
        self._validate_env_vars()
        self.jira = JIRA(
            os.getenv('JIRA_SERVER'),
            basic_auth=(os.getenv('JIRA_EMAIL'), os.getenv('JIRA_API_TOKEN'))
        )

    def _validate_env_vars(self):
        """Validate that all required environment variables are set."""
        required_vars = ['JIRA_SERVER', 'JIRA_EMAIL', 'JIRA_API_TOKEN']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            print(f"Error: Missing required environment variables: {', '.join(missing_vars)}")
            sys.exit(1)

    def _get_start_date(self, issue):
        """Extract start date from custom field."""
        start_date = issue.fields.customfield_11018
        return datetime.strptime(start_date, "%Y-%m-%d") if start_date else None

    def _get_complete_changelog(self, issue_key):
        """Get complete changelog for an issue."""
        all_histories = []
        server = self.jira._options['server']
        api_endpoint = f"{server}/rest/api/2/issue/{issue_key}/changelog"
        
        start_at = 0
        max_results = 100
        
        while True:
            response = self.jira._session.get(
                api_endpoint,
                params={
                    'startAt': start_at,
                    'maxResults': max_results
                }
            )
            
            if not response.ok:
                break
                
            data = response.json()
            if 'values' not in data or not data['values']:
                break
                
            histories = data['values']
            all_histories.extend(histories)
            
            if len(histories) < max_results or start_at + len(histories) >= data.get('total', 0):
                break
                
            start_at += max_results
        
        return all_histories

    def _get_in_progress_date(self, issue_key):
        """Get the date when the issue was moved to In Progress."""
        histories = self._get_complete_changelog(issue_key)
        
        for history in histories:
            for item in history['items']:
                if item['field'] == 'status' and item.get('toString', '').lower() == 'in progress':
                    return datetime.strptime(history['created'].split('T')[0], "%Y-%m-%d")
        return None

    def _get_issues_in_epic(self, epic_key):
        """Get all issues in an epic, handling pagination."""
        all_issues = []
        start_at = 0
        max_results = 100
        
        while True:
            issues_page = self.jira.search_issues(
                f'"Epic Link" = {epic_key}',
                startAt=start_at,
                maxResults=max_results
            )
            
            if not issues_page:
                break
                
            all_issues.extend(issues_page)
            
            if len(issues_page) < max_results:
                break
                
            start_at += max_results
        
        return all_issues

    def _get_earliest_issue_in_progress_date(self, epic_key):
        """Get the earliest In Progress date among all issues in an epic."""
        all_issues = self._get_issues_in_epic(epic_key)
        earliest_date = None
        
        for issue in all_issues:
            in_progress_date = self._get_in_progress_date(issue.key)
            if in_progress_date and (not earliest_date or in_progress_date < earliest_date):
                earliest_date = in_progress_date
                
        return earliest_date

    def analyze_epic(self, epic_key):
        """Analyze dates for an epic."""
        epic = self.jira.issue(epic_key)
        start_date = self._get_start_date(epic)
        epic_in_progress = self._get_in_progress_date(epic_key)
        first_issue_in_progress = self._get_earliest_issue_in_progress_date(epic_key)
        
        print(f"\nAnalysis for Epic {epic_key}:")
        print(f"Epic Start Date: {start_date.date() if start_date else 'Not set'}")
        print(f"Epic moved to In Progress: {epic_in_progress.date() if epic_in_progress else 'Never'}")
        print(f"First issue moved to In Progress: {first_issue_in_progress.date() if first_issue_in_progress else 'No issues in progress'}")

    def analyze_deliverable(self, deliverable_key):
        """Analyze dates for a deliverable."""
        deliverable = self.jira.issue(deliverable_key)
        start_date = self._get_start_date(deliverable)
        deliverable_in_progress = self._get_in_progress_date(deliverable_key)
        
        epics = self.jira.search_issues(f'parent = {deliverable_key} AND type = Epic')
        
        print(f"\nAnalysis for Deliverable {deliverable_key}:")
        print(f"Deliverable Start Date: {start_date.date() if start_date else 'Not set'}")
        print(f"Deliverable moved to In Progress: {deliverable_in_progress.date() if deliverable_in_progress else 'Never'}")
        
        if not epics:
            print("\nNo epics found in this deliverable")
            return
            
        print("\nContained Epics:")
        earliest_epic = None
        earliest_epic_start = None
        
        for epic in epics:
            epic_start = self._get_start_date(epic)
            epic_in_progress = self._get_in_progress_date(epic.key)
            earliest_issue_in_progress = self._get_earliest_issue_in_progress_date(epic.key)
            
            print(f"\nEpic {epic.key}:")
            print(f"  Start Date: {epic_start.date() if epic_start else 'Not set'}")
            print(f"  Moved to In Progress: {epic_in_progress.date() if epic_in_progress else 'Never'}")
            print(f"  First issue moved to In Progress: {earliest_issue_in_progress.date() if earliest_issue_in_progress else 'No issues in progress'}")
            
            if epic_start and (not earliest_epic_start or epic_start < earliest_epic_start):
                earliest_epic_start = epic_start
                earliest_epic = epic

def main():
    if len(sys.argv) != 2:
        print("Usage: python script.py <issue-key>")
        sys.exit(1)
        
    issue_key = sys.argv[1]
    analyzer = JiraDateAnalyzer()
    
    try:
        issue = analyzer.jira.issue(issue_key)
        
        if issue.fields.issuetype.name == 'Epic':
            analyzer.analyze_epic(issue_key)
        elif issue.fields.issuetype.name == 'Deliverable':
            analyzer.analyze_deliverable(issue_key)
        else:
            print(f"Issue type {issue.fields.issuetype.name} is not supported. Only Epic and Deliverable are supported.")
            
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()