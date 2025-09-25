"""
Jellyfish client for interacting with Jellyfish API
"""

import os
import json
from typing import List, Dict
from datetime import datetime
import requests
from date_utils import get_weekly_lookback_range, get_friday_of_week

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

    def get_work_items_by_category(
        self,
        work_category_slug: str,
        start_date: str,
        end_date: str,
        team_ids: list[str] | None = None,
    ) -> List[Dict]:
        """
        Fetch work items for a specific category (e.g., 'deliverable-new' or 'epics')
        across one or more team_ids. Falls back to self.team_id if team_ids is None.
        """
        url = f"{self.base_url}/delivery/work_category_contents"

        # Base params used for each request
        base_params = {
            "format": "json",
            "start_date": start_date,
            "end_date": end_date,
            "series": "false",
            "work_category_slug": work_category_slug,
            "completed_only": "false",
            "inprogress_only": "false",
            "view_archived": "false",
        }

        # Normalize + guard scope
        if team_ids is None and self.team_id:
            team_ids = [str(self.team_id)]
        team_ids = [str(t).strip() for t in (team_ids or []) if str(t).strip()]
        if not team_ids:
            raise ValueError("get_work_items_by_category: no team_ids provided (and self.team_id not set).")

        all_items: List[Dict] = []

        # One request per team_id
        for tid in team_ids:
            params = dict(base_params)
            params["team_id"] = tid  # scope the request

            print(f"\n=== CALLING API for {work_category_slug} (team_id={tid}) ===")
            print(f"URL: {url}")
            print(f"Params: {params}")

            try:
                response = requests.get(url, headers=self.headers, params=params, timeout=30)
                print(f"Response status: {response.status_code}")

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

                response.raise_for_status()
                data = response.json()

                # ---- Parse items  ----
                items: List[Dict] = []
                if isinstance(data, dict):
                    if "deliverables" in data:
                        items = data.get("deliverables", [])
                    elif "epics" in data:
                        items = data.get("epics", [])
                    else:
                        key_guess = "epics" if "epic" in work_category_slug.lower() else "deliverables"
                        items = data.get(key_guess, [])
                elif isinstance(data, list):
                    merged: List[Dict] = []
                    for bucket in data:
                        if isinstance(bucket, dict):
                            if "deliverables" in bucket:
                                bucket_items = bucket.get("deliverables", [])
                            elif "epics" in bucket:
                                bucket_items = bucket.get("epics", [])
                            else:
                                key_guess = "epics" if "epic" in work_category_slug.lower() else "deliverables"
                                bucket_items = bucket.get(key_guess, [])
                            merged.extend(bucket_items or [])
                    items = merged
                else:
                    items = data if isinstance(data, list) else []

                # Tag provenance and collect
                for it in items:
                    it.setdefault("_source_team_ids", [])
                    if tid not in it["_source_team_ids"]:
                        it["_source_team_ids"].append(tid)
                all_items.extend(items)

            except requests.exceptions.RequestException as e:
                print(f"ERROR: Request failed for work_category_slug='{work_category_slug}' (team_id={tid})")
                print(f"Error message: {e}")
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
                continue  # next team_id

            except Exception as e:
                print(f"UNEXPECTED ERROR in get_work_items_by_category({work_category_slug}, team_id={tid}): {type(e).__name__}: {e}")
                import traceback; traceback.print_exc()
                continue

        # Deduplicate across teams by source_issue_key
        seen = set()
        unique: List[Dict] = []
        dups = 0
        for it in all_items:
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
