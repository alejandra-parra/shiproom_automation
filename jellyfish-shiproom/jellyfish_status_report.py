#!/usr/bin/env python3
"""
Jellyfish Status Report Generator
Generates Google Sheets status reports for engineering teams based on Jellyfish data
"""

from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any
import argparse
from dotenv import load_dotenv
import os
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))

from clients.google_slides import GoogleSlidesClient
from clients.jira import JiraClient
from clients.jellyfish import JellyfishClient
from config.config_loader import load_config, load_teams_config, get_team_config, get_all_teams, validate_team_config
from utils.date_utils import format_date, get_report_date_range, get_weekly_lookback_range
from utils.table_utils import prepare_merged_table
from utils.filter_utils import filter_items, format_excluded_items_for_display
from utils.due_date_utils import format_due_date_with_history
from utils.status_utils import STATUS_MAPPING

class StatusReportGenerator:
    """Generates status reports from Jellyfish data"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.jellyfish = JellyfishClient(config)
        self.jira = JiraClient(config)
        self.slides = GoogleSlidesClient(config)
        
        # Status mapping for Google Sheets
        self.status_mapping = STATUS_MAPPING
        
        # Load teams configuration
        teams_config_path = config.get('teams_config_file', 'teams_config.yaml')
        self.teams_config = load_teams_config(teams_config_path)
        
        # Get team selection
        self.team_selection = config.get('team_selection', 'all')
    
    def get_formatted_due_date(self, current_date: str, issue_key: str) -> Tuple[str, List[Dict]]:
        """Get formatted due date with history for an issue"""
        # Get due date history from Jira
        date_history = self.jira.get_due_date_history(issue_key)
        return format_due_date_with_history(current_date, date_history)
    
    def generate_slide_for_team(self, team_identifier: str, team_config: Dict[str, Any]) -> None:
        """Generate a single slide for a specific team"""
        print(f"\n=== Generating slide for team: {team_identifier} ===")
        
        # Validate team configuration
        if not validate_team_config(team_config, team_identifier):
            print(f"Skipping team {team_identifier} due to invalid configuration")
            return
        
        # Update Jellyfish client with team-specific configuration
        self.jellyfish.team_id = team_config['team_id']
        self.jellyfish.team_name = team_config['team_name']
        
        start_date, end_date = get_report_date_range()
        print(f"Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        print(f"Fetching deliverables for team {self.jellyfish.team_name}...")
        
        deliverables = self.jellyfish.get_work_items_by_category(
            "deliverable-new",
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        )
        
        print(f"Total deliverables received from API: {len(deliverables)}")
        
        # Add due date history and labels to deliverables
        print(f"Adding due date history and labels to {len(deliverables)} deliverables...")
        for i, deliverable in enumerate(deliverables, 1):
            issue_key = deliverable.get('source_issue_key')
            if issue_key:
                print(f"  [{i}/{len(deliverables)}] Fetching due date history and labels for deliverable {issue_key}...")
                try:
                    deliverable['date_history'] = self.jira.get_due_date_history(issue_key)
                    deliverable['labels'] = self.jira.get_issue_labels(issue_key)
                    print(f"  [{i}/{len(deliverables)}] ✓ Due date history and labels fetched for {issue_key}")
                except Exception as e:
                    print(f"  [{i}/{len(deliverables)}] ✗ Error fetching due date history and labels for {issue_key}: {e}")
                    deliverable['date_history'] = []
                    deliverable['labels'] = []
            else:
                print(f"  [{i}/{len(deliverables)}] No issue key for deliverable, skipping due date history and labels")
                deliverable['date_history'] = []
                deliverable['labels'] = []
        
        print(f"Due date history and labels processing completed for deliverables")
        
        # Get the lookback range based on the completed week
        lookback_start, lookback_end = get_weekly_lookback_range(end_date)
        print(f"Using lookback range: {lookback_start.strftime('%Y-%m-%d')} to {lookback_end.strftime('%Y-%m-%d')}")
        
        filtered_deliverables, excluded_deliverables = filter_items(deliverables, lookback_start, lookback_end)
        print(f"Deliverables after filtering: {len(filtered_deliverables)}")
        
        print(f"Fetching epics for team {self.jellyfish.team_name}...")
        epics_response = self.jellyfish.get_work_items_by_category(
            "epics",
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        )
        
        print(f"Total epics received from API: {len(epics_response)}")
        
        # Add due date history and labels to epics
        print(f"Adding due date history and labels to {len(epics_response)} epics...")
        for i, epic in enumerate(epics_response, 1):
            issue_key = epic.get('source_issue_key')
            if issue_key:
                print(f"  [{i}/{len(epics_response)}] Fetching due date history and labels for epic {issue_key}...")
                try:
                    epic['date_history'] = self.jira.get_due_date_history(issue_key)
                    epic['labels'] = self.jira.get_issue_labels(issue_key)
                    print(f"  [{i}/{len(epics_response)}] ✓ Due date history and labels fetched for {issue_key}")
                except Exception as e:
                    print(f"  [{i}/{len(epics_response)}] ✗ Error fetching due date history and labels for {issue_key}: {e}")
                    epic['date_history'] = []
                    epic['labels'] = []
            else:
                print(f"  [{i}/{len(epics_response)}] No issue key for epic, skipping due date history and labels")
                epic['date_history'] = []
                epic['labels'] = []
        
        print(f"Due date history and labels processing completed for epics")
        
        filtered_epics, excluded_epics = filter_items(epics_response, lookback_start, lookback_end)
        print(f"Epics after filtering: {len(filtered_epics)}")
        
        print(f"Total items to include in report: {len(filtered_deliverables) + len(filtered_epics)}")
        
        # Determine slide ID
        slide_id = team_config.get('slide_id')
        if slide_id:
            # Strip 'id.' prefix if present (Google Slides API doesn't need it)
            if slide_id.startswith('id.'):
                slide_id = slide_id[3:]  # Remove 'id.' prefix
                print(f"Stripped 'id.' prefix from slide ID: {slide_id}")
            print(f"Using existing slide ID: {slide_id}")
            try:
                self.slides.clear_slide_content(slide_id)
            except Exception as e:
                print(f"Warning: Could not clear slide content: {e}")
                print("Slide may not exist - creating new slide...")
                slide_id = self.slides.create_slide()
                if slide_id:
                    print(f"NEW SLIDE CREATED: {slide_id} - Please add this to teams_config.yaml for team {team_identifier}")
                else:
                    print(f"Error: Failed to create new slide for team {team_identifier}")
                    return
        else:
            print("No slide ID provided - creating new slide")
            slide_id = self.slides.create_slide()
            if slide_id:
                print(f"NEW SLIDE CREATED: {slide_id} - Please add this to teams_config.yaml for team {team_identifier}")
            else:
                print(f"Error: Failed to create new slide for team {team_identifier}")
                return
        
        # Add title to slide
        self.slides.add_title(slide_id, f"{self.jellyfish.team_name} - Status Report", 50, 20)
        
        # Prepare merged table
        merged_data, formatting_map, color_map, merge_map, link_map = prepare_merged_table(
            filtered_deliverables, 
            filtered_epics,
            self.get_formatted_due_date
        )
        
        y_position = 80
        print(f"Merged table data: {len(merged_data)} rows")
        
        # Add merged table
        table_result = self.slides.add_table(
            slide_id,
            merged_data,
            50,
            y_position,
            formatting_map,
            color_map,
            {},  # header_color handled per-row in formatting_map
            merge_map=merge_map or [],
            link_map=link_map or {}
        )
        
        if table_result[0] is None:
            print("Error: Failed to create table")
            return
            
        table_id, table_dimensions, column_widths, total_table_width = table_result
        
        # Add Risks/Mitigations section to the right of the table
        margin = 20
        text_box_x = 50 + total_table_width + margin
        text_box_y = y_position
        text_box_height = table_dimensions['height'] if table_dimensions else 220
        slide_width = 960
        max_text_box_width = max(100, slide_width - text_box_x - 30)
        text_box_width = min(220, max_text_box_width)
        
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
        
        print(f"Slide generated for team {team_identifier}")
    
    def generate_slides(self):
        """Generate Google Slides status reports based on team selection"""
        if self.team_selection == 'all':
            print("Generating slides for all teams...")
            all_teams = get_all_teams(self.teams_config)
            
            for team_identifier, team_config in all_teams:
                self.generate_slide_for_team(team_identifier, team_config)
            
            print(f"\nCompleted generating slides for all teams")
        else:
            # Generate slide for specific team
            team_config = get_team_config(self.teams_config, self.team_selection)
            if team_config:
                self.generate_slide_for_team(self.team_selection, team_config)
                print(f"\nCompleted generating slide for team {self.team_selection}")
            else:
                print(f"Error: Team '{self.team_selection}' not found in teams configuration")
                print("Available teams:")
                all_teams = get_all_teams(self.teams_config)
                for team_id, _ in all_teams:
                    print(f"  - {team_id}")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Generate Jellyfish status report')
    parser.add_argument('--config', required=True, help='Path to config file')
    parser.add_argument('--team', help='Team identifier (e.g., BBEE, TOL, CLIP) or "all" for all teams')
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    
    # Override team selection if provided via command line
    if args.team:
        config['team_selection'] = args.team
    
    # Generate report
    generator = StatusReportGenerator(config)
    generator.generate_slides()

if __name__ == '__main__':
    main()