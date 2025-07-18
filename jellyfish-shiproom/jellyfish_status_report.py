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
        # Use returned column_widths and total_width for text box placement
        table_x = 50
        table_id, table_dims, column_widths, total_table_width = self.slides.add_table(
            slide_id,
            merged_data,
            table_x,
            y_position,
            formatting_map,
            color_map,
            {},  # header_color - empty dict for default behavior
            merge_map=merge_map,
            link_map=link_map
        )
        margin = 20
        text_box_x = table_x + total_table_width + margin
        text_box_y = y_position
        text_box_height = table_dims['height'] if table_dims else 220
        slide_width = 960
        max_text_box_width = max(100, slide_width - text_box_x - 30)
        text_box_width = min(220, max_text_box_width)
        print(f"DEBUG: Text box x={text_box_x}, y={text_box_y}, width={text_box_width}, height={text_box_height}")
        # === Placement configuration for Risks/Mitigations section ===
        # Offset to move the Risks/Mitigations title higher or lower relative to the table top
        RISKS_TITLE_VERTICAL_OFFSET = -22  # Move up/down (negative = up)
        RISKS_TITLE_HORIZONTAL_OFFSET = -5  # Move left/right (negative = left, positive = right)
        RISKS_TITLE_FONT_SIZE = 10
        RISKS_TITLE_HEIGHT = 18  # Height for one line of text at font size 10
        RISKS_CONTENT_GAP = 4    # Gap between title and content box
        RISKS_CONTENT_FONT_SIZE = 7
        RISKS_CONTENT_BORDER_WEIGHT = 0.5
        RISKS_CONTENT_BORDER_COLOR = {'red': 0, 'green': 0, 'blue': 0}
        RISKS_CONTENT_INITIAL_TEXT = "- "
        RISKS_CONTENT_HEIGHT = 260  # Set the height of the risks/mitigations content box (adjust as needed)
        # Calculate coordinates for Risks/Mitigations title and content box
        risks_title_x = text_box_x + RISKS_TITLE_HORIZONTAL_OFFSET
        risks_title_y = text_box_y + RISKS_TITLE_VERTICAL_OFFSET
        risks_title_width = text_box_width
        risks_title_height = RISKS_TITLE_HEIGHT
        risks_content_x = text_box_x
        risks_content_y = risks_title_y + risks_title_height + RISKS_CONTENT_GAP
        risks_content_width = text_box_width
        risks_content_height = RISKS_CONTENT_HEIGHT

        # --- Add Risks/Mitigations Title ---
        risks_title_text = "Risks / Mitigations"
        risks_title_id = self.slides.add_text_box(
            slide_id,
            risks_title_text,
            risks_title_x,
            risks_title_y,
            risks_title_width,
            risks_title_height
        )
        self.slides.update_textbox_style(risks_title_id, font_size=RISKS_TITLE_FONT_SIZE, bold=True)

        # --- Add Risks/Mitigations Content Box ---
        risks_content_id = self.slides.add_bordered_text_box(
            slide_id,
            RISKS_CONTENT_INITIAL_TEXT,
            risks_content_x,
            risks_content_y,
            risks_content_width,
            risks_content_height,
            border_color=RISKS_CONTENT_BORDER_COLOR,
            border_weight=RISKS_CONTENT_BORDER_WEIGHT
        )
        self.slides.update_textbox_style(risks_content_id, font_size=RISKS_CONTENT_FONT_SIZE, bold=False)
        
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