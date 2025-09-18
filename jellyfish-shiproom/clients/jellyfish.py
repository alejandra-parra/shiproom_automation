"""
Jellyfish client for interacting with Jellyfish API
"""

import os
import json
from typing import List, Dict
from datetime import datetime
import requests
from utils.date_utils import get_weekly_lookback_range, get_friday_of_week

class JellyfishClient:
    """Client for interacting with Jellyfish API"""

    def __init__(self, config: Dict):
        # Base URL and API key from env
        self.base_url = os.getenv('JELLYFISH_BASE_URL', '').rstrip('/')
        api_key = os.getenv('JELLYFISH_API_KEY', '')

        if not api_key:
            raise ValueError("JELLYFISH_API_KEY environment variable not set")
        if not self.base_url:
            raise ValueError("JELLYFISH_BASE_URL environment variable not set")

        # Allow switching between "Token" and "Bearer" via env
        scheme = os.getenv("JF_AUTH_SCHEME", "Token")

        self.headers = {
            "Authorization": f"{scheme} {api_key}",
            "accept": "application/json",
            "User-Agent": "jf-shiproom-script/1.0"
        }

        # Team info set per team by caller
        self.team_id = None
        self.team_name = None

        print(f"Initialized with base_url: {self.base_url}")
        print(f"Auth scheme: {scheme}")
        print("Team info will be set dynamically for each team")

    def get_work_items_by_category(self, work_category_slug: str,
                                   start_date: str, end_date: str) -> List[Dict]:
        """Fetch work items for a specific category (e.g., 'deliverable-new' or 'epics')."""
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
        }
        if self.team_id:
            params["team_id"] = self.team_id
        else:
            print("WARNING: team_id is not set on the JellyfishClient; request may be rejected or too broad.")

        print(f"\n=== CALLING API for {work_category_slug} ===")
        print(f"URL: {url}")
        print(f"Params: {params}")

        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            print(f"Response status: {response.status_code}")

            # Print error body BEFORE raising, so we always see the reason
            if response.status_code >= 400:
                ct = response.headers.get("Content-Type", "")
                print(f"Error response content-type: {ct}")
                if "json" in ct.lower():
                    try:
                        err_json = response.json()
                        print("Error response JSON (trimmed):")
                        print(json.dumps(err_json, indent=2)[:2000])
                    except Exception:
                        print("Error response (raw text, trimmed):")
                        print(response.text[:2000] if isinstance(response.text, str) else str(response.content)[:2000])
                else:
                    try:
                        print("Error response (raw text, trimmed):")
                        print(response.text[:2000])
                    except Exception:
                        print("Error response (bytes, trimmed):")
                        print(str(response.content)[:2000])

            # Will raise for 4xx/5xx and flow to except with context
            response.raise_for_status()

            data = response.json()
            print(f"Response type: {type(data)}")
            print(f"Response length: {len(data) if isinstance(data, list) else 'Not a list'}")

            # Use the lookback info only for logging/reference
            today = datetime.now()
            friday = get_friday_of_week(today)
            lookback_start, lookback_end = get_weekly_lookback_range(friday)
            print(f"\nUsing 7-day lookback range: {lookback_start.strftime('%Y-%m-%d')} to {lookback_end.strftime('%Y-%m-%d')}")

            # Extract items depending on structure & slug
            items: List[Dict] = []
            if isinstance(data, dict):
                if "deliverables" in data:
                    items = data.get("deliverables", [])
                    print(f"Number of deliverables found: {len(items)}")
                elif "epics" in data:
                    items = data.get("epics", [])
                    print(f"Number of epics found: {len(items)}")
                else:
                    key_guess = "epics" if "epic" in work_category_slug.lower() else "deliverables"
                    items = data.get(key_guess, [])
                    print(f"Keys present: {list(data.keys())}")
                    print(f"Number of items found via key guess '{key_guess}': {len(items)}")
            elif isinstance(data, list):
                print("\nResponse is a list (time-bucketed); aggregating items…")
                merged: List[Dict] = []
                for idx, bucket in enumerate(data):
                    if isinstance(bucket, dict):
                        bucket_items = []
                        if "deliverables" in bucket:
                            bucket_items = bucket.get("deliverables", [])
                        elif "epics" in bucket:
                            bucket_items = bucket.get("epics", [])
                        else:
                            key_guess = "epics" if "epic" in work_category_slug.lower() else "deliverables"
                            bucket_items = bucket.get(key_guess, [])
                        merged.extend(bucket_items or [])
                        tf = bucket.get("timeframe", {})
                        print(f"  Bucket {idx+1}: {tf.get('start','?')} → {tf.get('end','?')} | +{len(bucket_items)} items")
                    else:
                        print(f"  Bucket {idx+1}: unexpected type {type(bucket)} (skipping)")
                items = merged
                print(f"Total merged items: {len(items)}")
            else:
                print("Unexpected response structure; attempting to treat as a list")
                items = data if isinstance(data, list) else []
                print(f"Items coerced length: {len(items)}")

            print(f"Found {len(items)} items in the response")

            # Deduplicate by source_issue_key
            if items:
                seen = set()
                unique: List[Dict] = []
                dups = 0
                for it in items:
                    k = it.get("source_issue_key")
                    if k and k not in seen:
                        seen.add(k)
                        unique.append(it)
                    elif k:
                        dups += 1
                items = unique
                print(f"Deduplication: removed {dups} duplicates, kept {len(items)} unique items")

            if items:
                first = items[0]
                print("\nSample item structure:")
                print(f"Keys: {list(first.keys())}")
                print(json.dumps(first, indent=2, default=str)[:500] + "...")
            else:
                print("\nNo items found in response!")
                try:
                    print("Full response structure (trimmed):")
                    print(json.dumps(data, indent=2, default=str)[:1000] + "...")
                except Exception:
                    pass

            return items

        except requests.exceptions.RequestException as e:
            print(f"ERROR: Request failed for work_category_slug='{work_category_slug}'")
            print(f"Error message: {e}")

            # Context
            try:
                auth_header = self.headers.get("Authorization", "")
                auth_scheme = auth_header.split()[0] if auth_header else "UNKNOWN"
                print(f"Auth scheme in use: {auth_scheme} (token redacted)")
            except Exception:
                pass
            print(f"Base URL: {self.base_url}")

            resp = getattr(e, "response", None)
            if resp is not None:
                print(f"Response status: {resp.status_code}")
                try:
                    print(f"Response content-type: {resp.headers.get('Content-Type', '')}")
                except Exception:
                    pass
                try:
                    parsed = resp.json()
                    print("Response JSON (trimmed):")
                    print(json.dumps(parsed, indent=2)[:2000])
                except Exception:
                    try:
                        print("Response text (trimmed):")
                        print(resp.text[:2000])
                    except Exception:
                        print("No response body available.")
            else:
                print("No HTTP response object available (likely connection error or timeout).")

            print("Hint: Try switching auth scheme (Token ↔︎ Bearer), verify base URL root (/api vs /endpoints/export/{v}),")
            print("      test without team_id or with a known-good team, and verify work_category_slug.")
            return []

        except Exception as e:
            print(f"UNEXPECTED ERROR in get_work_items_by_category({work_category_slug}): {type(e).__name__}: {e}")
            import traceback; traceback.print_exc()
            return []
