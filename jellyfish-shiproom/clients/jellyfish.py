"""
Jellyfish client for interacting with Jellyfish API
"""

import os
import requests
from typing import List, Dict
from datetime import datetime, timedelta
import json

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
            
            # Extract deliverables from ONLY the last timeframe (most recent week)
            all_items = []
            if data:
                # Get only the last week's data
                last_week = data[-1]
                last_timeframe = last_week.get('timeframe', {})
                print(f"\nUsing ONLY last week: {last_timeframe.get('start')} to {last_timeframe.get('end')}")
                
                items = last_week.get('deliverables', [])
                print(f"Found {len(items)} items in last week")
                all_items = items
            
            print(f"\nTotal items to process: {len(all_items)}")
            
            # Debug: Show structure of first item
            if all_items:
                print(f"\nSample item structure:")
                first_item = all_items[0]
                print(f"Keys: {list(first_item.keys())}")
                print(f"Sample item: {json.dumps(first_item, indent=2, default=str)[:500]}...")
            
            return all_items
            
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