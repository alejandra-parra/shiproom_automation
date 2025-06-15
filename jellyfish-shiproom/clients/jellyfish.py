"""
Jellyfish client for interacting with Jellyfish API
"""

import os
import requests
from typing import List, Dict
from datetime import datetime, timedelta

class JellyfishClient:
    """Client for interacting with Jellyfish API"""
    
    def __init__(self, config: Dict):
        # Get Jellyfish credentials from environment variables only
        jellyfish_api_key = os.getenv('JELLYFISH_API_KEY')
        jellyfish_org_id = os.getenv('JELLYFISH_ORG_ID')
        
        if not all([jellyfish_api_key, jellyfish_org_id]):
            raise ValueError("JELLYFISH_API_KEY and JELLYFISH_ORG_ID environment variables must be set")
        
        self.api_key = jellyfish_api_key
        self.org_id = jellyfish_org_id
        self.base_url = "https://api.jellyfish.co/v1"
        print(f"Initialized Jellyfish client for org ID: {jellyfish_org_id}")
    
    def get_work_items_by_category(self, work_category_slug: str, 
                                 start_date: str, end_date: str) -> List[Dict]:
        """Get work items for a specific category and date range"""
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            params = {
                'organization_id': self.org_id,
                'work_category_slug': work_category_slug,
                'start_date': start_date,
                'end_date': end_date
            }
            
            response = requests.get(
                f"{self.base_url}/work_items",
                headers=headers,
                params=params
            )
            
            response.raise_for_status()
            return response.json().get('work_items', [])
            
        except Exception as e:
            print(f"Error getting work items: {e}")
            return [] 