#!/usr/bin/env python3
"""
Test script for calling the Jellyfish API
Fetches work items for a team and prints the output

Usage:
    python3 test_jellyfish_api.py [team_key]
    ./run_jellyfish_test.sh [team_key]

Examples:
    ./run_jellyfish_test.sh           # Uses AHOY team by default
    ./run_jellyfish_test.sh BBEE      # Uses BBEE team
    ./run_jellyfish_test.sh GROOT     # Uses GROOT team

Available teams: AHOY, BBEE, CAP, CAPI, CFISO, CLIP, CSTORE, DX, EXT, 
                 FUS, GROOT, HEJO, INTEG, KRK, MEC, MOGWAI, MOI, PIC, 
                 SPA, TOL, UFO, NT, EXA, ARC
"""

import os
import sys
import json
import yaml
from datetime import datetime, timedelta
from dotenv import load_dotenv
from jellyfish import JellyfishClient
from date_utils import get_report_date_range, get_weekly_lookback_range

# Load environment variables
load_dotenv()

def load_team_config(team_key="AHOY"):
    """Load team configuration from teams_config.yaml"""
    try:
        with open("teams_config.yaml", "r") as f:
            teams_config = yaml.safe_load(f)
        
        if team_key not in teams_config.get("teams", {}):
            print(f"✗ Team '{team_key}' not found in teams_config.yaml")
            print(f"Available teams: {', '.join(teams_config.get('teams', {}).keys())}")
            return None
        
        team_data = teams_config["teams"][team_key]
        
        # Handle both single team_id and multiple team_ids
        if "team_id" in team_data:
            team_ids = [str(team_data["team_id"])]
        elif "team_ids" in team_data:
            team_ids = [str(tid) for tid in team_data["team_ids"]]
        else:
            print(f"✗ No team_id or team_ids found for team '{team_key}'")
            return None
        
        return {
            "team_key": team_key,
            "team_ids": team_ids,
            "team_name": team_data.get("team_name", team_key),
            "presenter": team_data.get("presenter", "N/A"),
            "domain": team_data.get("domain", "N/A")
        }
    except Exception as e:
        print(f"✗ Error loading team config: {e}")
        return None

def main():
    print("=" * 80)
    print("Jellyfish API Test Script")
    print("=" * 80)
    
    # Get team key from command line or use default
    team_key = sys.argv[1] if len(sys.argv) > 1 else "AHOY"
    
    # Load team configuration
    team_config = load_team_config(team_key)
    if not team_config:
        return
    
    print(f"\nTeam Key: {team_config['team_key']}")
    print(f"Team: {team_config['team_name']}")
    print(f"Team ID(s): {', '.join(team_config['team_ids'])}")
    print(f"Presenter: {team_config['presenter']}")
    print(f"Domain: {team_config['domain']}\n")
    
    # Initialize the Jellyfish client
    try:
        config = {}  # Empty config, client reads from env vars
        client = JellyfishClient(config)
        print("✓ Jellyfish client initialized successfully\n")
    except Exception as e:
        print(f"✗ Failed to initialize Jellyfish client: {e}")
        return
    
    # Get date range for the current week
    _, report_end_date = get_report_date_range()
    start_date, end_date = get_weekly_lookback_range(report_end_date)
    
    # Convert datetime to string format for API
    start_date_str = start_date.strftime("%Y-%m-%d")
    end_date_str = end_date.strftime("%Y-%m-%d")
    print(f"Date Range: {start_date_str} to {end_date_str}\n")
    
    # Test fetching deliverables
    print("=" * 80)
    print("FETCHING DELIVERABLES (deliverable-new)")
    print("=" * 80)
    
    try:
        deliverables = client.get_work_items_by_category(
            work_category_slug="deliverable-new",
            start_date=start_date_str,
            end_date=end_date_str,
            team_ids=team_config["team_ids"]
        )
        
        print(f"\n✓ Successfully fetched {len(deliverables)} deliverables\n")
        
        if deliverables:
            print("Sample deliverable (first item):")
            print("-" * 80)
            print(json.dumps(deliverables[0], indent=2, default=str))
            print("-" * 80)
            
            # Print summary of all deliverables
            print("\nAll Deliverables Summary:")
            print("-" * 80)
            for i, item in enumerate(deliverables, 1):
                key = item.get('source_issue_key', 'N/A')
                summary = item.get('name', 'N/A')
                status = item.get('status', 'N/A')
                print(f"{i}. [{key}] {summary}")
                print(f"   Status: {status}")
                print()
        else:
            print("No deliverables found for this team in the specified date range.")
    
    except Exception as e:
        print(f"✗ Error fetching deliverables: {e}")
        import traceback
        traceback.print_exc()
    
    # Test fetching epics
    print("\n" + "=" * 80)
    print("FETCHING EPICS")
    print("=" * 80)
    
    try:
        epics = client.get_work_items_by_category(
            work_category_slug="epics",
            start_date=start_date_str,
            end_date=end_date_str,
            team_ids=team_config["team_ids"]
        )
        
        print(f"\n✓ Successfully fetched {len(epics)} epics\n")
        
        if epics:
            print("Sample epic (first item):")
            print("-" * 80)
            print(json.dumps(epics[0], indent=2, default=str))
            print("-" * 80)
            
            # Print summary of all epics
            print("\nAll Epics Summary:")
            print("-" * 80)
            for i, item in enumerate(epics, 1):
                key = item.get('source_issue_key', 'N/A')
                summary = item.get('name', 'N/A')
                status = item.get('status', 'N/A')
                print(f"{i}. [{key}] {summary}")
                print(f"   Status: {status}")
                print()
        else:
            print("No epics found for this team in the specified date range.")
    
    except Exception as e:
        print(f"✗ Error fetching epics: {e}")
        import traceback
        traceback.print_exc()
    
    print("=" * 80)
    print("Test Complete")
    print("=" * 80)

if __name__ == "__main__":
    main()