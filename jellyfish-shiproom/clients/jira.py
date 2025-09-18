"""
Jira client for interacting with Jira API
"""

import os
from typing import List, Dict, Optional
from jira import JIRA


class JiraClient:
    """Client for interacting with Jira API to get issue metadata"""

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
            print("Warning: Jira credentials not configured. Jira data will not be fetched.")
            self.jira = None

        # Hardcode your custom field id for Maturity here
        # e.g. "customfield_13790"
        self.maturity_field_id: Optional[str] = "customfield_13790"

    # -----------------------------
    # Labels
    # -----------------------------
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
            issue = self.jira.issue(issue_key, fields='labels')
            labels = getattr(issue.fields, 'labels', []) or []
            return labels
        except Exception as e:
            print(f"Error getting labels for {issue_key}: {e}")
            return []

    # -----------------------------
    # Due date history
    # -----------------------------
    def get_due_date_history(self, issue_key: str) -> List[Dict]:
        """
        Get the history of due date changes for an issue in chronological order.
        Only includes the last change per day to filter out accidental/temporary changes.
        Includes only due date changes on/after the issue moved to an "In Progress"-like status.
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
            max_results = 100
            max_pages = 10
            seen_history_ids = set()

            page_count = 0
            while page_count < max_pages:
                issue_with_changelog = self.jira.issue(
                    issue_key,
                    expand=f'changelog[{start_at}:{start_at + max_results}]'
                )

                if not hasattr(issue_with_changelog.changelog, 'histories') or not issue_with_changelog.changelog.histories:
                    break

                histories_in_page = len(issue_with_changelog.changelog.histories)
                current_history_ids = {h.id for h in issue_with_changelog.changelog.histories}
                if current_history_ids.issubset(seen_history_ids):
                    break

                all_histories.extend(issue_with_changelog.changelog.histories)
                seen_history_ids.update(current_history_ids)

                if histories_in_page < max_results:
                    break

                start_at += max_results
                page_count += 1

            # Find when the issue was moved to "In Progress" status and what the due date was at that time
            in_progress_timestamp = None
            original_due_at_in_progress = None
            current_tracked_due = None

            for history in sorted(all_histories, key=lambda x: x.created):
                for item in history.items:
                    if item.field.lower() in ['duedate', 'due date']:
                        current_tracked_due = item.toString
                    elif item.field.lower() in ['status', 'statuscategorychangedate']:
                        to_status = (item.toString or "").lower()
                        if any(s in to_status for s in ['in progress', 'active', 'started']):
                            in_progress_timestamp = history.created
                            original_due_at_in_progress = current_tracked_due
                            break
                if in_progress_timestamp:
                    break

            # Collect due date changes (oldest first)
            changes = []
            for history in all_histories:
                created = history.created
                for item in history.items:
                    if item.field.lower() in ['duedate', 'due date']:
                        changes.append({'timestamp': created, 'from': item.fromString, 'to': item.toString})
            changes.sort(key=lambda x: x['timestamp'])

            # Filter on/after "In Progress"
            if in_progress_timestamp:
                changes = [c for c in changes if c['timestamp'] >= in_progress_timestamp]

            if not changes:
                if current_due:
                    return [{'date': current_due, 'timestamp': None}]
                return []

            due_dates = []

            # Include original due at In Progress if different from current
            if original_due_at_in_progress:
                original_norm = original_due_at_in_progress.split(' ')[0] if ' ' in original_due_at_in_progress else original_due_at_in_progress
                current_norm = current_due.split(' ')[0] if current_due and ' ' in current_due else current_due
                if original_norm != current_norm:
                    due_dates.append({'date': original_due_at_in_progress, 'timestamp': in_progress_timestamp})

            # Keep only the last change per day (use the "to" value)
            daily_changes = {}
            for change in changes:
                date_key = change['timestamp'][:10]
                daily_changes[date_key] = change

            for change in sorted(daily_changes.values(), key=lambda x: x['timestamp']):
                if change['to']:
                    due_dates.append({'date': change['to'], 'timestamp': change['timestamp']})

            # Ensure current due is present
            if current_due:
                current_norm = current_due.split(' ')[0] if ' ' in current_due else current_due
                if not any((d['date'].split(' ')[0] if ' ' in d['date'] else d['date']) == current_norm for d in due_dates):
                    due_dates.append({
                        'date': current_due,
                        'timestamp': changes[-1]['timestamp'] if changes else None
                    })

            return due_dates

        except Exception as e:
            print(f"Error getting history for {issue_key}: {e}")
            return []

    # -----------------------------
    # Maturity (custom field)
    # -----------------------------
    def get_issue_maturity(self, issue_key: str) -> str:
        """
        Fetch the 'Maturity' custom field from Jira.
        Handles single-select, multi-select, and text/number.
        """
        if not self.jira:
            return ""
        if not self.maturity_field_id:
            return ""

        try:
            issue = self.jira.issue(issue_key, fields=self.maturity_field_id)
        except Exception as e:
            print(f"Warn: could not load maturity for {issue_key}: {e}")
            return ""

        val = getattr(issue.fields, self.maturity_field_id, None)
        # DEBUG (keep during integration; remove later if noisy)
        print(f"[maturity] {issue_key} -> {val!r}")

        if val is None:
            return ""

        # Single-select option object
        if hasattr(val, "value"):
            return str(val.value)

        # Multi-select options
        if isinstance(val, (list, tuple)):
            return ", ".join(str(v.value if hasattr(v, "value") else v) for v in val if v)

        # Plain string/number fallback
        return str(val)
