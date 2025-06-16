"""
Jellyfish client for interacting with Jellyfish API
"""

import os
import requests
from typing import List, Dict
from datetime import datetime, timedelta
import json
from utils.date_utils import get_weekly_lookback_range

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
            "unit": "week",
            "series": "true",
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
            
            # Find the last completed week (where end date is in the past)
            today = datetime.now()
            last_completed_week = None
            week_end_date = None
            
            for week in reversed(data):
                timeframe = week.get('timeframe', {})
                end_date_str = timeframe.get('end')
                if end_date_str:
                    try:
                        # Handle both Z and +00:00 timezone formats
                        end_date_str = end_date_str.replace('Z', '+00:00')
                        week_end = datetime.fromisoformat(end_date_str)
                        if week_end < today:
                            last_completed_week = week
                            week_end_date = week_end
                            print(f"\nUsing last completed week: {timeframe.get('start')} to {timeframe.get('end')}")
                            break
                    except Exception as e:
                        print(f"Error parsing end date {end_date_str}: {e}")
            
            if not last_completed_week:
                print("No completed weeks found in the response!")
                return []
            
            # Get the 7-day lookback range based on the Friday of the completed week
            lookback_start, lookback_end = get_weekly_lookback_range(week_end_date)
            print(f"\nUsing 7-day lookback range: {lookback_start.strftime('%Y-%m-%d')} to {lookback_end.strftime('%Y-%m-%d')}")
            
            items = last_completed_week.get('deliverables', [])
            print(f"Found {len(items)} items in last completed week")
            
            # Debug: Show structure of first item
            if items:
                print(f"\nSample item structure:")
                first_item = items[0]
                print(f"Keys: {list(first_item.keys())}")
                print(f"Sample item: {json.dumps(first_item, indent=2, default=str)[:500]}...")
            
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