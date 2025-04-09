"""Analyzer for Epic-level due date shifts."""

from typing import List, Dict, Optional
from datetime import datetime
import logging

from .base_analyzer import BaseJiraAnalyzer
from .models import StartDateScenario, AnalysisResult, DateShift, StartDates
from .utils import parse_jira_datetime
from .config import jira_settings

logger = logging.getLogger(__name__)

class EpicAnalyzer(BaseJiraAnalyzer):
    """Analyzes due date shifts for Epics."""
    
    def get_epics(self, project_key: str, start_date: str, end_date: str) -> List[Dict]:
        """Fetch epics for a specific project and date range."""
        try:
            jql = f"""
            type = Epic 
            AND project = {project_key}
            AND status = Done
            AND resolved >= {start_date}
            AND resolved <= {end_date}
            ORDER BY resolved ASC
            """
            logger.info(f"Fetching epics with JQL: {jql}")
            issues = self.jira.search_issues(jql, expand='changelog')
            logger.info(f"Found {len(issues)} epics resolved between {start_date} and {end_date}")
            return issues
        except Exception as e:
            logger.error(f"Error fetching epics: {e}")
            raise
    
    def get_epic_issues(self, epic_key: str) -> List[Dict]:
        """Fetch all issues belonging to an epic."""
        try:
            all_issues = []
            start_at = 0
            max_results = 100
            
            while True:
                jql = f'parent = {epic_key} ORDER BY created ASC'
                logger.info(f"Fetching issues for epic {epic_key} (batch starting at {start_at})")
                
                issues_page = self.jira.search_issues(
                    jql, 
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
            
            logger.info(f"Found {len(all_issues)} issues for epic {epic_key}")
            return all_issues
            
        except Exception as e:
            logger.error(f"Error fetching issues for epic {epic_key}: {e}")
            return []
    
    def find_epic_in_progress_date(self, epic) -> Optional[datetime]:
        """Find the first date when the epic was moved to 'In Progress'."""
        try:
            histories = self._get_complete_changelog(epic.key)
            for history in histories:
                for item in history['items']:
                    if (item['field'] == 'status' and 
                        item.get('toString', '').lower() == 'in progress'):
                        progress_date = parse_jira_datetime(history['created'], f"progress date for {epic.key}")
                        logger.info(f"Found 'In Progress' date for epic {epic.key}: {progress_date}")
                        return progress_date
            
            logger.info(f"No 'In Progress' status change found for epic {epic.key}")
            return None
        except Exception as e:
            logger.error(f"Error finding 'In Progress' date for epic {epic.key}: {e}")
            return None
    
    def find_first_progress_date(self, issues) -> tuple:
        """Find the earliest date when any issue in the epic was moved to 'In Progress'."""
        earliest_date = None
        earliest_issue_key = None
        
        for issue in issues:
            try:
                histories = self._get_complete_changelog(issue.key)
                for history in histories:
                    for item in history['items']:
                        if (item['field'] == 'status' and 
                            item.get('toString', '').lower() == 'in progress'):
                            progress_date = parse_jira_datetime(history['created'], f"progress date for {issue.key}")
                            if earliest_date is None or progress_date < earliest_date:
                                earliest_date = progress_date
                                earliest_issue_key = issue.key
                                logger.debug(f"Found earlier 'In Progress' date from issue {issue.key}: {progress_date}")
            except Exception as e:
                logger.error(f"Error processing issue {issue.key}: {e}")
        
        if earliest_date:
            logger.info(f"Earliest 'In Progress' date found: {earliest_date} (Issue: {earliest_issue_key})")
        else:
            logger.info("No 'In Progress' dates found in any issues")
        
        # We need both pieces of information
        return earliest_date, earliest_issue_key
    
    def get_epic_start_dates(self, epic_key: str) -> StartDates:
        """Get all possible start dates for an epic."""
        try:
            # Use the deliverable_key parameter for our epic key
            result = StartDates(deliverable_key=epic_key)
            
            # Get the epic
            epic = self.jira.issue(epic_key)
            
            # 1. Get the configured start date field value
            start_date_field = getattr(epic.fields, jira_settings.start_date_field, None)
            if start_date_field:
                # Store in deliverable_start since that's what's available in StartDates
                result.deliverable_start = parse_jira_datetime(start_date_field, f"start date field for {epic_key}")
            
            # 2. Get the epic in progress date
            epic_progress_date = self.find_epic_in_progress_date(epic)
            if epic_progress_date:
                # Store in deliverable_in_progress since that's what's available in StartDates
                result.deliverable_in_progress = epic_progress_date
            
            # 3. Get child issues and find earliest in progress date
            issues = self.get_epic_issues(epic_key)
            if issues:
                earliest_date, earliest_issue_key = self.find_first_progress_date(issues)
                if earliest_date:
                    result.earliest_issue_in_progress = earliest_date
                    result.earliest_issue_key = earliest_issue_key
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting start dates for epic {epic_key}: {e}")
            return StartDates(epic_key=epic_key)
    
    def get_start_date(self, epic, scenario: StartDateScenario, start_dates: StartDates = None) -> datetime:
        """Determine the start date based on the selected scenario."""
        try:
            # Use provided start dates or get them if not provided
            dates = start_dates or self.get_epic_start_dates(epic.key)
            
            if scenario == StartDateScenario.DELIVERABLE_START_DATE:  # Using as EPIC_START_DATE
                # Map to deliverable_start in StartDates
                start_date = dates.deliverable_start
                if start_date:
                    logger.info(f"Using given start date for epic {epic.key}: {start_date}")
                    return start_date
                logger.warning(f"No start date field found for epic {epic.key}")
            
            elif scenario == StartDateScenario.EARLIEST_EPIC_START:  # Using as EPIC_IN_PROGRESS
                # Map to deliverable_in_progress in StartDates
                start_date = dates.deliverable_in_progress
                if start_date:
                    logger.info(f"Using epic 'In Progress' date for {epic.key}: {start_date}")
                    return start_date
                logger.warning(f"No 'In Progress' date found for epic {epic.key}")
            
            elif scenario == StartDateScenario.FIRST_ISSUE_IN_PROGRESS:
                start_date = dates.earliest_issue_in_progress
                if start_date:
                    logger.info(f"Using first issue 'In Progress' date for epic {epic.key}: {start_date} (Issue: {dates.earliest_issue_key})")
                    return start_date
                logger.warning(f"No issue 'In Progress' dates found for epic {epic.key}")
            
            # Fallback to creation date if no appropriate date found
            return parse_jira_datetime(epic.fields.created, f"creation date for {epic.key}")
            
        except Exception as e:
            logger.error(f"Error determining start date for {epic.key}: {e}")
            return parse_jira_datetime(epic.fields.created, f"creation date for {epic.key} (after error)")
    
    def analyze_due_date_shifts(
        self,
        project_key: str,
        start_date: str,
        end_date: str,
        scenario: StartDateScenario,
        show_start_dates: bool = False,
        **kwargs
    ) -> AnalysisResult:
        """Analyze due date shifts for epics during a specific period."""
        logger.info(f"Starting epic analysis for project {project_key}")
        logger.info(f"Time period: {start_date} to {end_date}")
        logger.info(f"Using start date scenario: {scenario}")
        
        all_shifts = []
        all_start_dates = []
        
        # Analyze epics
        epics = self.get_epics(project_key, start_date, end_date)
        logger.info(f"Analyzing {len(epics)} epics")
        
        for epic in epics:
            try:
                # Get all possible start dates for this epic once
                start_dates = self.get_epic_start_dates(epic.key)
                all_start_dates.append(start_dates)
                
                shifts = self.extract_date_shifts(epic)
                if shifts and shifts.shifts:
                    # Get the appropriate start date based on scenario
                    shifts.start_date = self.get_start_date(epic, scenario, start_dates)
                    all_shifts.append(shifts)
            except Exception as e:
                logger.error(f"Error analyzing epic {epic.key}: {e}")
        
        logger.info(f"Analysis complete. Found {len(all_shifts)} epics with due date shifts")
        
        return AnalysisResult(
            team=project_key,  # For epics, we use project_key as the team identifier
            project=project_key,
            scenario=scenario,
            period_start=parse_jira_datetime(start_date, "analysis start date"),
            period_end=parse_jira_datetime(end_date, "analysis end date"),
            date_shifts=all_shifts,
            start_dates=all_start_dates,
            show_start_dates=show_start_dates
        )