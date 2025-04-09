"""Base class for Jira analysis functionality."""

from typing import List, Dict, Optional
from datetime import datetime
import logging
from abc import ABC, abstractmethod

from jira import JIRA

from .models import StartDateScenario, DateShift, AnalysisResult, StartDates
from .config import jira_settings
from .utils import parse_jira_datetime

logger = logging.getLogger(__name__)

class BaseJiraAnalyzer(ABC):
    """Base class with common Jira analysis functionality."""
    
    def __init__(self):
        """Initialize the analyzer with Jira connection."""
        self.jira = JIRA(
            basic_auth=(jira_settings.email, jira_settings.api_token),
            server=jira_settings.server
        )
    
    def _get_complete_changelog(self, issue_key: str) -> List[Dict]:
        """Get complete changelog for an issue, handling pagination."""
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
                logger.error(f"Error fetching changelog for {issue_key}: {response.status_code}")
                break
                
            data = response.json()
            if 'values' not in data or not data['values']:
                break
                
            histories = data['values']
            all_histories.extend(histories)
            
            if len(histories) < max_results or start_at + len(histories) >= data.get('total', 0):
                break
                
            start_at += max_results
        
        logger.debug(f"Retrieved {len(all_histories)} changelog entries for {issue_key}")
        return all_histories
    
    def extract_date_shifts(self, issue, field: str = 'duedate') -> DateShift:
        """Extract all due date shifts from an issue's changelog."""
        logger.debug(f"Extracting date shifts for {issue.key}")
        start_date = parse_jira_datetime(issue.fields.created, f"creation date for {issue.key}")
        end_date = parse_jira_datetime(issue.fields.resolutiondate, f"resolution date for {issue.key}")
        shifts = []
        initial_due_date = None
        earliest_change_date = None
        
        histories = self._get_complete_changelog(issue.key)
        for history in histories:
            history_date = parse_jira_datetime(history['created'], f"history date for {issue.key}")
            
            for item in history['items']:
                if item['field'] == field and item.get('fromString'):
                    shift_date = parse_jira_datetime(item['fromString'], f"shift date for {issue.key}")
                    
                    # Only consider dates after the start date
                    if shift_date > start_date:
                        # Track initial due date based on earliest history date
                        if not earliest_change_date or history_date < earliest_change_date:
                            earliest_change_date = history_date
                            initial_due_date = shift_date
                            logger.info(f"Updated initial due date for {issue.key} to {initial_due_date} "
                                    f"based on change at {history_date}")
                        
                        # Add to shifts collection
                        shifts.append(shift_date)
                        logger.debug(f"Found valid due date shift for {issue.key} on {shift_date}")
                    else:
                        logger.debug(f"Ignoring due date shift before start date for {issue.key}: {shift_date}")
        
        if issue.fields.duedate:
            current_due_date = parse_jira_datetime(issue.fields.duedate, f"current due date for {issue.key}")
            shifts.append(current_due_date)
            
            # If we haven't found an initial due date yet, use the current due date
            if not initial_due_date:
                initial_due_date = current_due_date
                logger.debug(f"Using current due date as initial due date for {issue.key}: {initial_due_date}")
        
        if shifts:
            logger.info(f"Found {len(shifts)} valid due date shifts for {issue.key}{issue.fields.summary}")
        else:
            logger.debug(f"No valid due date shifts found for {issue.key}")
        
        return DateShift(
            issue_key=issue.key,
            issue_summary=issue.fields.summary,
            issue_type=issue.fields.issuetype.name,
            start_date=start_date,
            end_date=end_date,
            shifts=sorted(shifts),
            initial_due_date=initial_due_date  # Now we always pass this parameter
        )
    
    def get_epic_issues(self, epic_key: str) -> List[Dict]:
        """Get all issues belonging to an epic."""
        try:
            all_issues = []
            start_at = 0
            max_results = 100
            
            while True:
                issues_page = self.jira.search_issues(
                    f"'Epic Link' = {epic_key} ORDER BY created ASC",
                    startAt=start_at,
                    maxResults=max_results,
                    expand='changelog'
                )
                
                if not issues_page:
                    break
                    
                all_issues.extend(issues_page)
                
                if len(issues_page) < max_results:
                    break
                    
                start_at += max_results
            
            logger.debug(f"Found {len(all_issues)} issues in epic {epic_key}")
            return all_issues
            
        except Exception as e:
            logger.error(f"Error fetching issues for epic {epic_key}: {e}")
            return []
    
    def get_deliverable_start_dates(self, deliverable_key: str) -> StartDates:
        """Get all relevant start dates for a deliverable."""
        try:
            # Get deliverable details
            deliverable = self.jira.issue(deliverable_key)
            skip_deliverable = False
            
            # 1. Start date field of deliverable
            deliverable_start = parse_jira_datetime(deliverable.fields.customfield_11018, 
                                                f"start date field for {deliverable_key}")
            
            # 2. Date when moved to in progress
            deliverable_in_progress = None
            histories = self._get_complete_changelog(deliverable_key)
            for history in histories:
                for item in history['items']:
                    if (item['field'] == 'status' and 
                        item.get('toString', '').lower() == 'in progress'):
                        deliverable_in_progress = parse_jira_datetime(history['created'], 
                                                                    f"in progress date for {deliverable_key}")
                        break
                if deliverable_in_progress:
                    break
            
            # Get all epics in the deliverable
            epics = self.jira.search_issues(f'parent = {deliverable_key} AND type = Epic')
            
            earliest_epic = None
            earliest_epic_start = None
            earliest_epic_in_progress = None
            earliest_epic_in_progress_key = None
            earliest_issue_in_progress = None
            earliest_issue_key = None
            earliest_issue_epic_key = None
            
            # First pass: find earliest epic start and in-progress dates
            for epic in epics:
                # Check epic start date
                epic_start = parse_jira_datetime(epic.fields.customfield_11018, 
                                            f"start date field for {epic.key}")
                if epic_start and (not earliest_epic_start or epic_start < earliest_epic_start):
                    earliest_epic_start = epic_start
                    earliest_epic = epic.key
                
                # Check epic in progress date
                epic_in_progress = None
                epic_histories = self._get_complete_changelog(epic.key)
                for history in epic_histories:
                    for item in history['items']:
                        if (item['field'] == 'status' and 
                            item.get('toString', '').lower() == 'in progress'):
                            epic_in_progress = parse_jira_datetime(history['created'], 
                                                                f"in progress date for {epic.key}")
                            break
                    if epic_in_progress:
                        break
                
                if epic_in_progress and (not earliest_epic_in_progress or 
                                    epic_in_progress < earliest_epic_in_progress):
                    earliest_epic_in_progress = epic_in_progress
                    earliest_epic_in_progress_key = epic.key
            
            # Second pass: check all issues across all epics to find the earliest in-progress issue
            logger.info(f"Checking issues across all {len(epics)} epics in deliverable {deliverable_key} for earliest in-progress")
            
            for epic in epics:
                logger.debug(f"Checking issues in epic {epic.key}")
                epic_issues = self.get_epic_issues(epic.key)
                
                for issue in epic_issues:
                    histories = self._get_complete_changelog(issue.key)
                    for history in histories:
                        for item in history['items']:
                            if (item['field'] == 'status' and 
                                item.get('toString', '').lower() == 'in progress'):
                                issue_in_progress = parse_jira_datetime(history['created'], 
                                                                    f"in progress date for {issue.key}")
                                if (not earliest_issue_in_progress or 
                                    issue_in_progress < earliest_issue_in_progress):
                                    earliest_issue_in_progress = issue_in_progress
                                    earliest_issue_key = issue.key
                                    earliest_issue_epic_key = epic.key
                                    logger.debug(f"Found earlier in progress issue: {issue.key} in epic {epic.key} at {issue_in_progress}")
            
            # Log all findings
            logger.info(f"\nStart dates for Deliverable {deliverable_key}:")
            logger.info(f"1. Deliverable start date field: {deliverable_start}")
            logger.info(f"2. Deliverable moved to in progress: {deliverable_in_progress}")
            logger.info(f"3. Earliest epic start date field: {earliest_epic_start} (Epic: {earliest_epic})")
            logger.info(f"4. Earliest epic in progress date: {earliest_epic_in_progress} (Epic: {earliest_epic_in_progress_key})")
            logger.info(f"5. Earliest issue in progress date: {earliest_issue_in_progress} (Issue: {earliest_issue_key}, Epic: {earliest_issue_epic_key})")
            
            if(deliverable_in_progress == None and earliest_epic_start == None and earliest_epic_in_progress == None and earliest_issue_in_progress == None):
                skip_deliverable = True
                logger.info(f"Skipping epic {deliverable_key}")
            
            return StartDates(
                deliverable_key=deliverable_key,
                deliverable_start=deliverable_start,
                skip_deliverable=skip_deliverable,
                deliverable_in_progress=deliverable_in_progress,
                earliest_epic_start=earliest_epic_start,
                earliest_epic_in_progress=earliest_epic_in_progress,
                earliest_issue_in_progress=earliest_issue_in_progress,
                earliest_epic_key=earliest_epic,
                earliest_epic_in_progress_key=earliest_epic_in_progress_key,
                earliest_issue_key=earliest_issue_key
            )
            
        except Exception as e:
            logger.error(f"Error analyzing start dates for deliverable {deliverable_key}: {e}")
            return StartDates(
                deliverable_key=deliverable_key,
                deliverable_start=None,
                deliverable_in_progress=None,
                earliest_epic_start=None,
                earliest_epic_in_progress=None,
                earliest_issue_in_progress=None,
                earliest_epic_key=None,
                earliest_epic_in_progress_key=None,
                earliest_issue_key=None
            )
    
    @abstractmethod
    def get_start_date(self, issue, scenario: StartDateScenario) -> datetime:
        """Determine the start date based on the selected scenario."""
        pass
    
    @abstractmethod
    def analyze_due_date_shifts(
        self,
        project_key: str,
        start_date: str,
        end_date: str,
        scenario: StartDateScenario,
        show_start_dates: bool = False,
        **kwargs
    ) -> AnalysisResult:
        """Analyze due date shifts for issues during a specific period."""
        pass