"""
CSV-based client with Jira issues 
"""

import os
import pandas as pd
from typing import List, Dict
from datetime import datetime

class CSVClient:
    """Client for reading work items from CSV files instead of Jellyfish API"""

    def __init__(self, config: Dict):
        # Get CSV file path from environment variable
        self.csv_path = os.getenv('CSV_ISSUES_FILE_PATH', '')
        
        if not self.csv_path:
            raise ValueError("CSV_ISSUES_FILE_PATH environment variable not set")
        
        if not os.path.exists(self.csv_path):
            raise FileNotFoundError(f"CSV file not found at {self.csv_path}")

        # Team info set per team by caller (maintaining compatibility with JellyfishClient)
        self.jira_project_key = None
        self.team_name = None

        print(f"Initialized with CSV file: {self.csv_path}")
        print("Team info will be set dynamically for each team")

    def get_work_items_by_category(
        self,
        issue_type: str,
        start_date: str,
        end_date: str,
        jira_project_keys: list[str] | None = None,
    ) -> List[Dict]:
        """
        Read work items from CSV file for a specific category (e.g., 'deliverable' or 'epic')
        across one or more jira_project_keys. Falls back to self.jira_project_key if jira_project_keys is None.
        """
        # Normalize + guard scope (maintaining compatibility with CSVClient)
        if jira_project_keys is None and self.jira_project_key:
            jira_project_keys = [str(self.jira_project_key)]
        jira_project_keys = [str(t).strip() for t in (jira_project_keys or []) if str(t).strip()]
        if not jira_project_keys:
            raise ValueError("get_work_items_by_category: no jira_project_keys provided (and self.jira_project_key not set).")

        try:
            # Read CSV file
            print(f"\n=== Reading CSV for {issue_type} ===")
            df = pd.read_csv(self.csv_path)
            
            # Filter by work category if column exists
            if 'issue_type' in df.columns:
                df = df[df['issue_type'] == issue_type]
            
            # Convert jira_project_keys from string to list
            if 'jira_project_keys' in df.columns:
                df['_jira_project_keys'] = df['jira_project_keys'].fillna('').apply(
                    lambda x: [t.strip() for t in str(x).split(',') if t.strip()]
                )
            elif 'jira_project_key' in df.columns:
                df['_jira_project_keys'] = df['jira_project_key'].fillna('').apply(
                    lambda x: [t.strip() for t in str(x).split(',') if t.strip()]
                )
            # Convert labels to list if present
            if 'labels' in df.columns:
                df['labels'] = df['labels'].fillna('').apply(
                    lambda x: [l.strip() for l in str(x).split(',') if l.strip()]
                )
            
            # Convert DataFrame to list of dictionaries
            all_items = df.to_dict('records')
            
            # Filter by jira_project_keys
            filtered_items = []
            for item in all_items:
                item_teams = item.get('_jira_project_keys', [])
                if isinstance(item_teams, str):
                    item_teams = [t.strip() for t in item_teams.split(',') if t.strip()]
                if not item_teams:  # If no teams specified, item belongs to all teams
                    item['_jira_project_keys'] = jira_project_keys
                    filtered_items.append(item)
                else:
                    # Check if any of the requestedjira_project_keys match the item's teams
                    if any(team in item_teams for team in jira_project_keys):
                        item['_jira_project_keys'] = list(set(item_teams) & set(jira_project_keys))
                        filtered_items.append(item)
            
            # Filter by dates
            #if start_date and end_date:
            #    start = datetime.strptime(start_date, '%Y-%m-%d')
            #    end = datetime.strptime(end_date, '%Y-%m-%d')
            #    filtered_items = [
            #        item for item in filtered_items 
            #        if start <= datetime.strptime(item.get('created_date', start_date), '%Y-%m-%d') <= end
            #    ]
            print(f"Filtered items after date filter: {len(filtered_items)}")
            for item in filtered_items:
                print(item)
            # Deduplicate across teams by issue key (maintaining compatibility with JellyfishClient)
            seen = set()
            unique: List[Dict] = []
            dups = 0
            for it in filtered_items:
                k = it.get("issue_key")
                if k and k not in seen:
                    seen.add(k)
                    unique.append(it)
                elif k:
                    dups += 1
                    try:
                        for ex in unique:
                            if ex.get("issue_key") == k:
                                ex.setdefault("_jira_project_keys", [])
                                for sid in it.get("_jira_project_keys", []):
                                    if sid not in ex["_jira_project_keys"]:
                                        ex["_jira_project_keys"].append(sid)
                                break
                    except Exception:
                        pass

            # Normalize fields for compatibility with Jellyfish schema
            for it in unique:
                # Ensure 'issue_key' exists for downstream code
                if 'issue_key' not in it:
                    it['issue_key'] = it.get('issue_id')
                
                # convert singular csv column 'jira_project_key' -> _jira_project_keys
                if '_jira_project_keys' not in it:
                    raw = it.get('jira_project_keys') or it.get('jira_project_key') or ''
                    if isinstance(raw, str):
                        it['_jira_project_keys'] = [t.strip() for t in raw.split(',') if t.strip()]
                    elif isinstance(raw, list):
                        it['_jira_project_keys'] = raw
                    else:
                        it['_jira_project_keys'] = []
                
                # Ensure '_source_team_ids' exists
                it.setdefault('_source_team_ids', it.get('_jira_project_keys', []))

                # Ensure due_date exists (preserve CSV value); leave empty string if missing
                it['due_date'] = it.get('due_date', '') 

                # Ensure maturity exists
                it['maturity'] = it.get('maturity', 'N/A')

            print(f"Deduplication: removed {dups} duplicates, kept {len(unique)} unique items")
            return unique
            
        except Exception as e:
            print(f"Error reading CSV file: {str(e)}")
            import traceback
            traceback.print_exc()
            return []