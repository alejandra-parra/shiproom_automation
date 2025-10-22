"""
CSV-based client that mimics the Jellyfish API client interface
"""

import os
import pandas as pd
from typing import List, Dict
from datetime import datetime

class CSVClient:
    """Client for reading work items from CSV files instead of Jellyfish API"""

    def __init__(self, config: Dict):
        # Get CSV file path from environment variable
        self.csv_path = os.getenv('WORK_ITEMS_CSV_PATH', '')
        
        if not self.csv_path:
            raise ValueError("WORK_ITEMS_CSV_PATH environment variable not set")
        
        if not os.path.exists(self.csv_path):
            raise FileNotFoundError(f"CSV file not found at {self.csv_path}")

        # Team info set per team by caller (maintaining compatibility with JellyfishClient)
        self.team_id = None
        self.team_name = None

        print(f"Initialized with CSV file: {self.csv_path}")
        print("Team info will be set dynamically for each team")

    def get_work_items_by_category(
        self,
        work_category_slug: str,
        start_date: str,
        end_date: str,
        team_ids: list[str] | None = None,
    ) -> List[Dict]:
        """
        Read work items from CSV file for a specific category (e.g., 'deliverable-new' or 'epics')
        across one or more team_ids. Falls back to self.team_id if team_ids is None.
        """
        # Normalize + guard scope (maintaining compatibility with JellyfishClient)
        if team_ids is None and self.team_id:
            team_ids = [str(self.team_id)]
        team_ids = [str(t).strip() for t in (team_ids or []) if str(t).strip()]
        if not team_ids:
            raise ValueError("get_work_items_by_category: no team_ids provided (and self.team_id not set).")

        try:
            # Read CSV file
            print(f"\n=== Reading CSV for {work_category_slug} ===")
            df = pd.read_csv(self.csv_path)
            
            # Filter by work category if column exists
            if 'work_category_slug' in df.columns:
                df = df[df['work_category_slug'] == work_category_slug]
            
            # Convert team_ids from string to list
            if '_source_team_ids' in df.columns:
                df['_source_team_ids'] = df['_source_team_ids'].fillna('').apply(
                    lambda x: [t.strip() for t in str(x).split(',') if t.strip()]
                )
            
            # Convert labels to list if present
            if 'labels' in df.columns:
                df['labels'] = df['labels'].fillna('').apply(
                    lambda x: [l.strip() for l in str(x).split(',') if l.strip()]
                )
            
            # Convert DataFrame to list of dictionaries
            all_items = df.to_dict('records')
            
            # Filter by team_ids
            filtered_items = []
            for item in all_items:
                item_teams = item.get('_source_team_ids', [])
                if isinstance(item_teams, str):
                    item_teams = [t.strip() for t in item_teams.split(',') if t.strip()]
                if not item_teams:  # If no teams specified, item belongs to all teams
                    item['_source_team_ids'] = team_ids
                    filtered_items.append(item)
                else:
                    # Check if any of the requested team_ids match the item's teams
                    if any(team in item_teams for team in team_ids):
                        item['_source_team_ids'] = list(set(item_teams) & set(team_ids))
                        filtered_items.append(item)
            
            # Filter by dates
            if start_date and end_date:
                start = datetime.strptime(start_date, '%Y-%m-%d')
                end = datetime.strptime(end_date, '%Y-%m-%d')
                filtered_items = [
                    item for item in filtered_items 
                    if start <= datetime.strptime(item.get('created_date', start_date), '%Y-%m-%d') <= end
                ]
            
            # Deduplicate across teams by source_issue_key (maintaining compatibility with JellyfishClient)
            seen = set()
            unique: List[Dict] = []
            dups = 0
            for it in filtered_items:
                k = it.get("source_issue_key")
                if k and k not in seen:
                    seen.add(k)
                    unique.append(it)
                elif k:
                    dups += 1
                    try:
                        for ex in unique:
                            if ex.get("source_issue_key") == k:
                                ex.setdefault("_source_team_ids", [])
                                for sid in it.get("_source_team_ids", []):
                                    if sid not in ex["_source_team_ids"]:
                                        ex["_source_team_ids"].append(sid)
                                break
                    except Exception:
                        pass

            print(f"Deduplication: removed {dups} duplicates, kept {len(unique)} unique items")
            return unique
            
        except Exception as e:
            print(f"Error reading CSV file: {str(e)}")
            import traceback
            traceback.print_exc()
            return []