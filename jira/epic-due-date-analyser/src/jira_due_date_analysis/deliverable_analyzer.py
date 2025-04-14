"""Analyzer for Deliverable-level due date shifts."""

from typing import List, Dict, Optional
from datetime import datetime
import logging

from .base_analyzer import BaseJiraAnalyzer
from .models import StartDateScenario, AnalysisResult, StartDates
from .utils import parse_jira_datetime
from .config import jira_settings

logger = logging.getLogger(__name__)

class DeliverableAnalyzer(BaseJiraAnalyzer):
    """Analyzes due date shifts for Deliverables."""
    
    def find_first_progress_date(self, issues: List[Dict]) -> Optional[datetime]:
        """Find the earliest 'In Progress' date among a list of issues."""
        earliest_progress = None
        for issue in issues:
            histories = self._get_complete_changelog(issue.key)
            for history in histories:
                for item in history['items']:
                    if (item['field'] == 'status' and 
                        item.get('toString', '').lower() == 'in progress'):
                        progress_date = parse_jira_datetime(history['created'], f"progress date for {issue.key}")
                        if (earliest_progress is None or 
                            progress_date < earliest_progress):
                            earliest_progress = progress_date
                            logger.debug(f"Found earlier progress date from {issue.key}: {progress_date}")
        return earliest_progress
    
    def get_deliverables(self, team_label: str, start_date: str, end_date: str) -> List[Dict]:
        """Fetch deliverables for a specific team label and date range."""
        try:
            jql = f"""
            type = Deliverable 
            AND (
                (status = "Done" AND resolved >= {start_date} AND resolved <= {end_date})
                OR
                status = "In Progress"
            )
            AND labels = "{team_label}"
            """
            logger.info(f"Fetching deliverables with JQL: {jql}")
            issues = self.jira.search_issues(jql, expand='changelog')
            logger.info(f"Found {len(issues)} relevant deliverables since {start_date}")
            return issues
        except Exception as e:
            logger.error(f"Error fetching deliverables: {e}")
            raise
    
    def get_deliverable_epics(self, deliverable_key: str) -> List[Dict]:
        """Get all epic issues that belong to a deliverable."""
        try:
            all_epics = []
            start_at = 0
            max_results = 100
            
            while True:
                jql = f"parent = {deliverable_key} AND type = Epic ORDER BY created ASC"
                epics_page = self.jira.search_issues(
                    jql,
                    startAt=start_at,
                    maxResults=max_results,
                    expand='changelog'
                )
                
                if not epics_page:
                    break
                    
                all_epics.extend(epics_page)
                
                if len(epics_page) < max_results:
                    break
                    
                start_at += max_results
            
            logger.debug(f"Found {len(all_epics)} epics for deliverable {deliverable_key}")
            return all_epics
            
        except Exception as e:
            logger.error(f"Error fetching epics for deliverable {deliverable_key}: {e}")
            return []
    
    def get_start_date(self, deliverable, scenario: StartDateScenario, start_dates: StartDates = None) -> datetime:
        """Determine the start date based on the selected scenario."""
        try:
            # Use provided start dates or get them if not provided
            dates = start_dates or self.get_deliverable_start_dates(deliverable.key)
            
            if scenario == StartDateScenario.DELIVERABLE_START_DATE:
                start_date = dates.deliverable_start
                if start_date:
                    logger.info(f"Using deliverable start date for {deliverable.key}: {start_date}")
                    return start_date
                logger.warning(f"No start date field found for {deliverable.key}")
                
            elif scenario == StartDateScenario.EARLIEST_EPIC_START:
                start_date = dates.earliest_epic_start
                if start_date:
                    logger.info(f"Using earliest epic start date for {deliverable.key}: {start_date} (Epic: {dates.earliest_epic_key})")
                    return start_date
                logger.warning(f"No epic start dates found for {deliverable.key}")
                
            elif scenario == StartDateScenario.FIRST_ISSUE_IN_PROGRESS:
                start_date = dates.earliest_issue_in_progress
                if start_date:
                    logger.info(f"Using earliest issue in progress date for {deliverable.key}: {start_date} (Issue: {dates.earliest_issue_key})")
                    return start_date
                logger.warning(f"No issue in progress dates found for {deliverable.key}")
            
            # Fallback to creation date if no appropriate date found
            return parse_jira_datetime(deliverable.fields.created, f"creation date for {deliverable.key}")
            
        except Exception as e:
            logger.error(f"Error determining start date for {deliverable.key}: {e}")
            return parse_jira_datetime(deliverable.fields.created, f"creation date for {deliverable.key} (after error)")
    
    def analyze_due_date_shifts(
        self,
        project_key: str,
        start_date: str,
        end_date: str,
        scenario: StartDateScenario,
        team_label: str = None,
        show_start_dates: bool = False
    ) -> AnalysisResult:
        """Analyze due date shifts for deliverables during a specific period."""
        if team_label is None:
            raise ValueError("team_label is required for deliverable analysis")
            
        logger.info(f"Starting deliverable analysis for project {project_key} with team label {team_label}")
        logger.info(f"Time period: {start_date} to {end_date}")
        
        all_shifts = []
        all_start_dates = []
        
        # Analyze deliverables using team label
        deliverables = self.get_deliverables(team_label, start_date, end_date)
        logger.info(f"Analyzing {len(deliverables)} deliverables")
        
        for deliverable in deliverables:
            try:
                # Get all possible start dates for this deliverable once
                start_dates = self.get_deliverable_start_dates(deliverable.key)
                if start_dates.skip_deliverable == False:
                    all_start_dates.append(start_dates)
                    
                    shifts = self.extract_date_shifts(deliverable)
                    if shifts.shifts:
                        shifts.start_date = self.get_start_date(deliverable, scenario, start_dates)
                        all_shifts.append(shifts)
                else:
                    logger.info(f"Skipping {deliverable.key}")
            except Exception as e:
                logger.error(f"Error analyzing deliverable {deliverable.key}: {e}")
        
        logger.info(f"Analysis complete. Found {len(all_shifts)} deliverables with due date shifts")
        return AnalysisResult(
            team=team_label,
            project=project_key,
            scenario=scenario,
            period_start=parse_jira_datetime(start_date, "analysis start date"),
            period_end=parse_jira_datetime(end_date, "analysis end date"),
            date_shifts=all_shifts,
            start_dates=all_start_dates,
            show_start_dates=show_start_dates
        )