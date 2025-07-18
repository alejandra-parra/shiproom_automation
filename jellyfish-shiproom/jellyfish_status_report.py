#!/usr/bin/env python3
"""
Jellyfish Status Report Generator
Generates Google Sheets status reports for engineering teams based on Jellyfish data
"""

from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import argparse
from dotenv import load_dotenv

from clients.google_slides import GoogleSlidesClient
from clients.jira import JiraClient
from clients.jellyfish import JellyfishClient
from config.config_loader import load_config
from utils.date_utils import format_date, get_report_date_range, get_weekly_lookback_range
from utils.table_utils import prepare_merged_table
from utils.filter_utils import filter_items, format_excluded_items_for_display
from utils.due_date_utils import format_due_date_with_history
from utils.status_utils import STATUS_MAPPING

# Load environment variables
load_dotenv()

class StatusReportGenerator:
    """Generates status reports from Jellyfish data"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.jellyfish = JellyfishClient(config)
        self.jira = JiraClient(config)
        self.slides = GoogleSlidesClient(config)
        
        # Status mapping for Google Sheets
        self.status_mapping = STATUS_MAPPING
    
    def get_formatted_due_date(self, current_date: str, issue_key: str) -> Tuple[str, List[Dict]]:
        """Get formatted due date with history for an issue"""
        # Get due date history from Jira
        date_history = self.jira.get_due_date_history(issue_key)
        return format_due_date_with_history(current_date, date_history)
    
    def generate_slides(self):
        """Generate Google Slides status report with a single merged table"""
        start_date, end_date = get_report_date_range()
        print(f"Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        print(f"Fetching deliverables for team {self.jellyfish.team_name}...")
        deliverables = self.jellyfish.get_work_items_by_category(
            "deliverable-new",
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        )
        
        # Add due date history to deliverables
        for deliverable in deliverables:
            issue_key = deliverable.get('source_issue_key')
            if issue_key:
                deliverable['date_history'] = self.jira.get_due_date_history(issue_key)
        
        # Get the lookback range based on the completed week
        lookback_start, lookback_end = get_weekly_lookback_range(end_date)
        print(f"Using lookback range: {lookback_start.strftime('%Y-%m-%d')} to {lookback_end.strftime('%Y-%m-%d')}")
        
        filtered_deliverables, excluded_deliverables = filter_items(deliverables, lookback_start, lookback_end)
        print(f"Deliverables after filtering: {len(filtered_deliverables)}")
        print(f"Deliverables excluded: {len(excluded_deliverables)}")
        
        print(f"\nFetching epics for team {self.jellyfish.team_name}...")
        epics_response = self.jellyfish.get_work_items_by_category(
            "epics",
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        )
        
        # Add due date history to epics
        for epic in epics_response:
            issue_key = epic.get('source_issue_key')
            if issue_key:
                try:
                    epic['date_history'] = self.jira.get_due_date_history(issue_key)
                except Exception as e:
                    print(f"Error getting history for {issue_key}: {e}")
                    epic['date_history'] = []
            else:
                epic['date_history'] = []
        
        filtered_epics, excluded_epics = filter_items(epics_response, lookback_start, lookback_end)
        print(f"Epics after filtering: {len(filtered_epics)}")
        print(f"Epics excluded: {len(excluded_epics)}")
        
        print(f"\n=== FINAL SUMMARY ===")
        print(f"Total items to include in report: {len(filtered_deliverables) + len(filtered_epics)}")
        print(f"  - Deliverables: {len(filtered_deliverables)}")
        print(f"  - Epics: {len(filtered_epics)}")
        
        slide_id = self.slides.slide_id
        try:
            self.slides.clear_slide_content(slide_id)
        except Exception as e:
            print(f"Warning: Could not clear slide content: {e}")
            print("Continuing with existing content...")
        self.slides.add_title(slide_id, f"{self.jellyfish.team_name} - Status Report", 50, 20)
        # Prepare merged table
        merged_data, formatting_map, color_map, merge_map, link_map = prepare_merged_table(
            filtered_deliverables, 
            filtered_epics,
            self.get_formatted_due_date
        )
        y_position = 80
        print(f"Merged table data: {len(merged_data)} rows")
        # Add merged table (extend add_table to support merge_map if needed)
        table_id, table_dimensions = self.slides.add_table(
            slide_id,
            merged_data,
            50,
            y_position,
            formatting_map,
            color_map,
            {},  # header_color - empty dict for default behavior
            merge_map=merge_map,
            link_map=link_map
        )
        
        # Add exclusion log to the right of the table (outside visible area)
        all_excluded_items = excluded_deliverables + excluded_epics
        if all_excluded_items:
            exclusion_text = format_excluded_items_for_display(all_excluded_items)
            # Position the text box to the right of the table, outside the visible slide area
            # Google Slides dimensions are typically 720x405 points
            exclusion_x = 750  # Right side of the slide (slide width is ~720)
            exclusion_y = 20   # Top of the slide
            exclusion_width = 600  # Wide width to avoid line breaks
            exclusion_height = 400  # Reasonable height for multiple items
            
            self.slides.add_text_box(
                slide_id,
                f"EXCLUDED ITEMS:\n\n{exclusion_text}",
                exclusion_x,
                exclusion_y,
                exclusion_width,
                exclusion_height
            )
            print(f"Added exclusion log with {len(all_excluded_items)} items")
        
        print(f"Report generated in Google Slides")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Generate Jellyfish status report')
    parser.add_argument('--config', required=True, help='Path to config file')
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    
    # Generate report
    generator = StatusReportGenerator(config)
    generator.generate_slides()

if __name__ == '__main__':
    main()