#!/usr/bin/env python3
"""
Test script to demonstrate the shiproom label functionality
"""

from datetime import datetime, timedelta
from utils.filter_utils import filter_items

def test_shiproom_labels():
    """Test the shiproom label functionality with different scenarios"""
    
    # Create test data with different label combinations
    test_items = [
        {
            'source_issue_key': 'TEST-1',
            'name': 'Normal Roadmap Item',
            'source_issue_status': 'In Progress',
            'investment_classification': 'Roadmap',
            'completed_date': None,
            'target_date': '2025-08-01',
            'date_history': [],
            'labels': []  # No labels - should use normal criteria
        },
        {
            'source_issue_key': 'TEST-2',
            'name': 'Force Include Item',
            'source_issue_status': 'Backlog',  # Would normally be excluded
            'investment_classification': 'Maintenance',  # Would normally be excluded
            'completed_date': None,
            'target_date': '2025-08-01',
            'date_history': [],
            'labels': ['shiproom_include']  # Should force include
        },
        {
            'source_issue_key': 'TEST-3',
            'name': 'Force Exclude Item',
            'source_issue_status': 'In Progress',
            'investment_classification': 'Roadmap',
            'completed_date': None,
            'target_date': '2025-08-01',
            'date_history': [],
            'labels': ['shiproom_exclude']  # Should force exclude
        },
        {
            'source_issue_key': 'TEST-4',
            'name': 'Both Labels Item',
            'source_issue_status': 'In Progress',
            'investment_classification': 'Roadmap',
            'completed_date': None,
            'target_date': '2025-08-01',
            'date_history': [],
            'labels': ['shiproom_include', 'shiproom_exclude']  # Both labels - should use normal criteria
        },
        {
            'source_issue_key': 'TEST-5',
            'name': 'Other Labels Item',
            'source_issue_status': 'In Progress',
            'investment_classification': 'Roadmap',
            'completed_date': None,
            'target_date': '2025-08-01',
            'date_history': [],
            'labels': ['other_label', 'another_label']  # Other labels - should use normal criteria
        }
    ]
    
    # Set up lookback period
    lookback_end = datetime.now()
    lookback_start = lookback_end - timedelta(days=7)
    
    print("=== Testing Shiproom Label Functionality ===\n")
    
    # Process each test item
    for item in test_items:
        print(f"Testing: {item['name']}")
        print(f"  Issue Key: {item['source_issue_key']}")
        print(f"  Status: {item['source_issue_status']}")
        print(f"  Investment: {item['investment_classification']}")
        print(f"  Labels: {item['labels']}")
        
        # Apply filtering logic manually to show what happens
        labels = item.get('labels', [])
        has_shiproom_include = 'shiproom_include' in labels
        has_shiproom_exclude = 'shiproom_exclude' in labels
        
        print(f"  Has shiproom_include: {has_shiproom_include}")
        print(f"  Has shiproom_exclude: {has_shiproom_exclude}")
        
        if has_shiproom_exclude and not has_shiproom_include:
            print(f"  RESULT: Force EXCLUDED (shiproom_exclude label)")
        elif has_shiproom_include and not has_shiproom_exclude:
            print(f"  RESULT: Force INCLUDED (shiproom_include label)")
        else:
            # Use normal criteria
            if "Roadmap" not in item['investment_classification']:
                print(f"  RESULT: EXCLUDED (not a roadmap item)")
            elif item['source_issue_status'] not in ["In Progress", "In Review"]:
                print(f"  RESULT: EXCLUDED (not in progress or in review)")
            else:
                print(f"  RESULT: INCLUDED (meets normal criteria)")
        
        print()
    
    # Now test with the actual filter function
    print("=== Running Actual Filter Function ===\n")
    filtered_items, excluded_items = filter_items(test_items, lookback_start, lookback_end)
    
    print(f"Filtered items: {len(filtered_items)}")
    for item in filtered_items:
        print(f"  ✓ {item['source_issue_key']}: {item['name']} (Status: {item.get('_status', 'Unknown')})")
    
    print(f"\nExcluded items: {len(excluded_items)}")
    for item in excluded_items:
        print(f"  ✗ {item['issue_key']}: {item['name']} - {item['exclusion_reason']}")

if __name__ == '__main__':
    test_shiproom_labels() 