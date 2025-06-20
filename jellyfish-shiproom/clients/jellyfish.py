"""
Jellyfish client for interacting with Jellyfish API
"""

import os
import requests
from typing import List, Dict
from datetime import datetime, timedelta
import json
from utils.date_utils import get_weekly_lookback_range, get_friday_of_week

class JellyfishClient:
    """Client for interacting with Jellyfish API"""
    
    def __init__(self, config: Dict):
        # Get Jellyfish credentials from environment variables only
        self.base_url = os.getenv('JELLYFISH_BASE_URL', '').rstrip('/')
        
        # Authorization is just the API key directly
        api_key = os.getenv('JELLYFISH_API_KEY', '')
        
        if not api_key:
            raise ValueError("JELLYFISH_API_KEY environment variable not set")
        
        if not self.base_url:
            raise ValueError("JELLYFISH_BASE_URL environment variable not set")
        
        self.headers = {
            "Authorization": "Token "+api_key,
            "accept": "application/json"
        }
        
        # Team info comes from config file
        self.team_id = config.get('team', {}).get('team_id', '')
        self.team_name = config.get('team', {}).get('team_name', '')
        
        if not self.team_id:
            raise ValueError("Jellyfish team ID not found in config file under 'team.team_id'")
        
        print(f"Initialized with base_url: {self.base_url}")
        print(f"Team ID: {self.team_id}")
        print(f"Team Name: {self.team_name}")
    
    def get_work_items_by_category(self, work_category_slug: str, 
                                   start_date: str, end_date: str) -> List[Dict]:
        """Fetch work items for a specific category (deliverable-new or epic)"""
        url = f"{self.base_url}/delivery/work_category_contents"
        params = {
            "format": "json",
            "start_date": start_date,
            "end_date": end_date,
            "series": "false",
            "work_category_slug": work_category_slug,
            "completed_only": "false",
            "inprogress_only": "false",
            "view_archived": "false",
            "team_id": self.team_id
        }
        
        print(f"\n=== CALLING API for {work_category_slug} ===")
        print(f"URL: {url}")
        print(f"Params: {params}")
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            print(f"Response status: {response.status_code}")
            response.raise_for_status()
            data = response.json()
            
            print(f"Response type: {type(data)}")
            print(f"Response length: {len(data) if isinstance(data, list) else 'Not a list'}")
            
            # If it's empty, show that
            if not data:
                print("Response is empty!")
                return []
            
            # Since we removed unit=week, we get one result instead of weekly data
            # Get the 7-day lookback range based on the previous Friday (or today if it's Friday)
            today = datetime.now()
            friday = get_friday_of_week(today)
            lookback_start, lookback_end = get_weekly_lookback_range(friday)
            print(f"\nUsing 7-day lookback range: {lookback_start.strftime('%Y-%m-%d')} to {lookback_end.strftime('%Y-%m-%d')}")
            
            # The response should now be a single object with deliverables
            if isinstance(data, dict):
                items = data.get('deliverables', [])
                print(f"\nResponse is a dictionary with keys: {list(data.keys())}")
                print(f"Number of deliverables found: {len(items)}")
            elif isinstance(data, list) and len(data) == 1:
                # Handle the case where we get a single-element array with the entire month's data
                print(f"\nResponse is a single-element array (entire month)")
                month_data = data[0]
                if isinstance(month_data, dict):
                    items = month_data.get('deliverables', [])
                    timeframe = month_data.get('timeframe', {})
                    print(f"  Month timeframe: {timeframe.get('start', 'unknown')} to {timeframe.get('end', 'unknown')}")
                    print(f"  Number of items in month: {len(items)}")
                else:
                    items = []
                    print(f"  Month data is not a dictionary")
            elif isinstance(data, list):
                # Fallback for multiple elements (shouldn't happen without unit=week)
                print(f"\nResponse is a list with {len(data)} items (unexpected)")
                items = []
                for week_data in data:
                    if isinstance(week_data, dict):
                        week_items = week_data.get('deliverables', [])
                        items.extend(week_items)
                        print(f"  Week {week_data.get('timeframe', {}).get('start', 'unknown')} to {week_data.get('timeframe', {}).get('end', 'unknown')}: {len(week_items)} items")
                print(f"Total items extracted from all weeks: {len(items)}")
            else:
                # Fallback in case the response structure is different
                items = data if isinstance(data, list) else []
                print(f"\nResponse is a list with {len(items)} items")
            
            print(f"Found {len(items)} items in the response")
            
            # Deduplicate items based on source_issue_key to avoid duplicates from multiple timeframes
            if items:
                seen_keys = set()
                unique_items = []
                duplicates_removed = 0
                
                for item in items:
                    issue_key = item.get('source_issue_key')
                    if issue_key and issue_key not in seen_keys:
                        seen_keys.add(issue_key)
                        unique_items.append(item)
                    elif issue_key:
                        duplicates_removed += 1
                
                items = unique_items
                print(f"Deduplication: Removed {duplicates_removed} duplicate items, kept {len(items)} unique items")
            
            # Debug: Show structure of first item
            if items:
                print(f"\nSample item structure:")
                first_item = items[0]
                print(f"Keys: {list(first_item.keys())}")
                print(f"Sample item: {json.dumps(first_item, indent=2, default=str)[:500]}...")
                
                # Show all items for debugging
                print(f"\nAll items summary:")
                for i, item in enumerate(items):
                    issue_key = item.get('source_issue_key', 'NO_KEY')
                    name = item.get('name', 'NO_NAME')
                    status = item.get('source_issue_status', 'NO_STATUS')
                    investment = item.get('investment_classification', 'NO_INVESTMENT')
                    print(f"  {i+1}. {issue_key}: {name[:50]}... | Status: {status} | Investment: {investment}")
            else:
                print(f"\nNo items found in response!")
                print(f"Full response structure: {json.dumps(data, indent=2, default=str)[:1000]}...")
            
            return items
            
        except requests.exceptions.RequestException as e:
            print(f"ERROR: Request failed for {work_category_slug}")
            print(f"Error message: {e}")
            if hasattr(e, 'response') and e.response:
                print(f"Response status: {e.response.status_code}")
                print(f"Response text: {e.response.text[:500]}...")
            return []
        except Exception as e:
            print(f"UNEXPECTED ERROR: {type(e)} - {e}")
            return [] 