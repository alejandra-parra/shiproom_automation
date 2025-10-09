#!/usr/bin/env python3
"""
Jellyfish Status Report Generator
Generates Google Sheets status reports for engineering teams based on Jellyfish data
"""

from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any
import argparse
import yaml
import logging

# --- Logging setup ---
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(filename)s:%(lineno)d %(message)s"
)
logger = logging.getLogger(__name__)

# --- Load secrets to access Google, Jira, Jellyfish header if set in .env ---

import os
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))

from google_slides import GoogleSlidesClient
from jira_client import JiraClient
from jellyfish import JellyfishClient
from config_loader import load_config, load_teams_config, get_team_config, get_all_teams, validate_team_config, get_team_ids
from date_utils import get_report_date_range, get_weekly_lookback_range
from table_utils import prepare_merged_table
from filter_utils import filter_items, format_excluded_items_for_display
from due_date_utils import format_due_date_with_history as format_due_epic, format_due_date_with_history_deliverable as format_due_deliv
from status_utils import STATUS_MAPPING
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from zoneinfo import ZoneInfo

BERLIN_TZ = ZoneInfo("Europe/Berlin")

def last_week_friday_str(today=None) -> str:
    """
    Returns YYYY-MM-DD for the Friday of the previous ISO week
    relative to 'today' in Europe/Berlin.
    ISO week: Mon=1 .. Sun=7
    """
    if today is None:
        today = datetime.now(BERLIN_TZ).date()
        logger.debug(f"Set today: {today}")
    monday_this_week = today - timedelta(days=today.isoweekday() - 1)
    logger.debug(f"Set monday_this_week: {monday_this_week}")
    monday_prev_week = monday_this_week - timedelta(days=7)
    logger.debug(f"Set monday_prev_week: {monday_prev_week}")
    friday_prev_week = monday_prev_week + timedelta(days=4)
    logger.debug(f"Set friday_prev_week: {friday_prev_week}")
    result = friday_prev_week.strftime("%Y-%m-%d")
    logger.debug(f"Set result: {result}")
    logger.debug("Completed: last_week_friday_str - main.py")
    return result

def duplicate_template_as_last_week_friday(slides_svc, drive_svc, template_id, parent_folder_id=None):
    """
    Duplicates the template and names it "<Template Title> - YYYY-MM-DD",
    where the date is last week's Friday (Europe/Berlin).
    Returns (archive_id, new_title).
    """
    logger.info("Starting duplicate_template_as_last_week_friday")
    meta = slides_svc.presentations().get(presentationId=template_id).execute()
    logger.debug(f"Set meta: {meta}")
    base_title = "Shiproom"
    logger.debug(f"Set base_title: {base_title}")
    date_str = last_week_friday_str()
    logger.debug(f"Set date_str: {date_str}")
    new_title = f"{date_str} - {base_title}"
    logger.debug(f"Set new_title: {new_title}")

    body = {"name": new_title}
    logger.debug(f"Set body: {body}")
    if parent_folder_id:
        body["parents"] = [parent_folder_id]
        logger.debug(f"Updated body with parents: {body}")
    logger.info(f"[COPY FROM PREVIOUS WEEK] title={new_title}  parent_folder_id={parent_folder_id or '(none)'}")

    try:
        copied = drive_svc.files().copy(
            fileId=template_id,
            body=body,
            supportsAllDrives=True
        ).execute()
        logger.debug(f"Set copied: {copied}")

        archive_id = copied["id"]
        logger.debug(f"Set archive_id: {archive_id}")
        meta = drive_svc.files().get(
            fileId=archive_id,
            fields="id,name,parents,driveId,owners(emailAddress,displayName),webViewLink",
            supportsAllDrives=True,
        ).execute()
        logger.debug(f"Updated meta: {meta}")

        logger.info("COPY META: name: %s, id: %s, driveId: %s, parents: %s, owners: %s, open: %s",
            meta.get("name"),
            meta.get("id"),
            meta.get("driveId"),
            meta.get("parents"),
            meta.get("owners"),
            meta.get("webViewLink"))
        
        logger.info(f"Archived: {new_title} → https://docs.google.com/presentation/d/{archive_id}/edit")
        logger.debug("Completed: duplicate_template_as_last_week_friday - main.py")
        return archive_id, new_title
    
    except HttpError as e:
        about = drive_svc.about().get(fields="user(emailAddress),storageQuota").execute()
        logger.error("[DRV ABOUT] user: %s quota: %s", about.get("user", {}), about.get("storageQuota", {}))
        logger.error("[ERROR] Drive copy failed: %s", e)
        logger.debug("Completed: duplicate_template_as_last_week_friday (exception) - main.py")
        raise

class StatusReportGenerator:
    """Generates status reports from Jellyfish data"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config or {}
        logger.debug(f"Set self.config: {self.config}")

        self.jellyfish = JellyfishClient(self.config)
        logger.debug(f"Set self.jellyfish: {self.jellyfish}")
        self.jira = JiraClient(self.config)
        logger.debug(f"Set self.jira: {self.jira}")
        self.slides = GoogleSlidesClient(self.config)
        logger.debug(f"Set self.slides: {self.slides}")

        self.status_mapping = STATUS_MAPPING
        logger.debug(f"Set self.status_mapping: {self.status_mapping}")

        teams_config_path = self.config.get('teams_config_file', 'teams_config.yaml')
        logger.debug(f"Set teams_config_path: {teams_config_path}")
        self.teams_config = load_teams_config(teams_config_path)
        logger.debug(f"Set self.teams_config: {self.teams_config}")
        self.team_selection = self.config.get('team_selection', 'all')
        logger.debug(f"Set self.team_selection: {self.team_selection}")

        slides_cfg = (self.config.get("google_slides") or {})
        logger.debug(f"Set slides_cfg: {slides_cfg}")
        template_id = slides_cfg.get("presentation_id")
        logger.debug(f"Set template_id: {template_id}")
        if not template_id:
            logger.error("Missing 'google_slides.presentation_id' in config")
            raise RuntimeError("Missing 'google_slides.presentation_id' in config")
        self.template_presentation_id = template_id
        logger.debug(f"Set self.template_presentation_id: {self.template_presentation_id}")
        self.presentation_id = template_id
        logger.debug(f"Set self.presentation_id: {self.presentation_id}")
        self.output_folder_id = os.getenv("GOOGLE_DRIVE_OUTPUT_FOLDER_ID") or slides_cfg.get("output_folder_id")
        logger.debug(f"Set self.output_folder_id: {self.output_folder_id}")

        logger.info("Output folder ID: %s", self.output_folder_id or "(none)")
        if not self.output_folder_id:
            logger.error("GOOGLE_DRIVE_OUTPUT_FOLDER_ID is not set. Without a destination folder, the copy goes to the service account’s My Drive (which usually has no storage).")
            raise RuntimeError(
                "GOOGLE_DRIVE_OUTPUT_FOLDER_ID is not set. Without a destination folder, "
                "the copy goes to the service account’s My Drive (which usually has no storage)."
            )

        creds = getattr(self.slides, "credentials", None)
        logger.debug(f"Set creds: {creds}")
        if creds is None:
            key_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
            logger.debug(f"Set key_path: {key_path}")
            if not key_path:
                logger.error("GOOGLE_APPLICATION_CREDENTIALS is not set")
                raise RuntimeError("GOOGLE_APPLICATION_CREDENTIALS is not set")
            scopes = [
                "https://www.googleapis.com/auth/presentations",
                "https://www.googleapis.com/auth/drive",
            ]
            logger.debug(f"Set scopes: {scopes}")
            creds = service_account.Credentials.from_service_account_file(key_path, scopes=scopes)
            logger.debug(f"Updated creds: {creds}")

        self.slides_svc = build("slides", "v1", credentials=creds)
        logger.debug(f"Set self.slides_svc: {self.slides_svc}")
        self.drive_svc  = build("drive",  "v3", credentials=creds)
        logger.debug(f"Set self.drive_svc: {self.drive_svc}")

        if hasattr(self.slides, "presentation_id"):
            self.slides.presentation_id = self.template_presentation_id
            logger.debug(f"Updated self.slides.presentation_id: {self.slides.presentation_id}")

        logger.info(f"Using permanent template (from config): {self.template_presentation_id}")

    def run(self):
        logger.info("Running StatusReportGenerator.run")
        duplicate_template_as_last_week_friday(
            self.slides_svc,
            self.drive_svc,
            self.template_presentation_id,
            self.output_folder_id
        )
        logger.info("Duplicated template as last week Friday")
        self.generate_slides()
        logger.info("Completed generate_slides")
        logger.debug("Completed: StatusReportGenerator.run - main.py")

    def generate_slide_for_team(self, team_identifier: str, team_config: Dict[str, Any]) -> None:
        """Generate a single slide for a specific team"""
        logger.info(f"\n=== Generating slide for team: {team_identifier} ===")
        
        # Validate team configuration
        if not validate_team_config(team_config, team_identifier):
            logger.warning(f"Skipping team {team_identifier} due to invalid configuration")
            return
        
        # Update Jellyfish client with team-specific configuration
        self.jellyfish.team_name = team_config['team_name']
        team_scope = get_team_ids(team_config)

        if not team_scope and 'team_id' in team_config:
            team_scope = [str(team_config['team_id'])]

        if not team_scope:
            logger.error(f"Error: no Jellyfish team IDs configured for {team_identifier}")
            return
        
        start_date, end_date = get_report_date_range()
        logger.info(f"Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        logger.info(f"Fetching deliverables for team {self.jellyfish.team_name}...")
        
        deliverables = self.jellyfish.get_work_items_by_category(
            "deliverable-new",
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d'),
            team_ids=team_scope
        )
        
        logger.info(f"Total deliverables received from API: {len(deliverables)}")
        
        # Add due date history, labels and maturity level to deliverables

        logger.info(f"Adding due date history, labels, and maturity to {len(deliverables)} deliverables...")
        for i, deliverable in enumerate(deliverables, 1):
            issue_key = deliverable.get('source_issue_key')
            if issue_key:
                logger.info(f"  [{i}/{len(deliverables)}] Fetching due date history, labels, maturity for deliverable {issue_key}...")
                try:
                    deliverable['date_history'] = self.jira.get_due_date_history(issue_key)
                    deliverable['labels'] = self.jira.get_issue_labels(issue_key)
                    deliverable['maturity'] = self.jira.get_issue_maturity(issue_key) or "N/A"

                    current_due = (
                        deliverable.get('target_date')
                        or deliverable.get('due_date')
                        or deliverable.get('current_due_date')
                    )
                    if current_due:
                        text, fmt = format_due_deliv(current_due, deliverable.get('date_history') or [])
                    else:
                        text, fmt = ("N/A", [])
                    deliverable['due_tape_text'] = text
                    deliverable['due_tape_fmt'] = fmt
                    logger.info(f"  [{i}/{len(deliverables)}] ✓ Metadata fetched for {issue_key} (maturity='{deliverable['maturity']}')")
                except Exception as e:
                    logger.warning(f"  [{i}/{len(deliverables)}] ✗ Error fetching metadata for {issue_key}: {e}")
                    deliverable['date_history'] = []
                    deliverable['labels'] = []
                    deliverable['maturity'] = "N/A"
                    deliverable['due_tape_text'] = "N/A"
                    deliverable['due_tape_fmt'] = []
            else:
                logger.info(f"  [{i}/{len(deliverables)}] No issue key for deliverable, skipping metadata")
                deliverable['date_history'] = []
                deliverable['labels'] = []
                deliverable['maturity'] = "N/A"
                deliverable['due_tape_text'] = "N/A"
                deliverable['due_tape_fmt'] = []

        logger.info(f"Due date history, labels and maturity processing completed for deliverables")
        
        # Get the lookback range based on the completed week
        lookback_start, lookback_end = get_weekly_lookback_range(end_date)
        logger.info(f"Using lookback range: {lookback_start.strftime('%Y-%m-%d')} to {lookback_end.strftime('%Y-%m-%d')}")
        
        filtered_deliverables, excluded_deliverables = filter_items(deliverables, lookback_start, lookback_end)
        logger.info(f"Deliverables after filtering: {len(filtered_deliverables)}")
        
        logger.info(f"Fetching epics for team {self.jellyfish.team_name}...")
        epics_response = self.jellyfish.get_work_items_by_category(
            "epics",
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d'),
            team_ids=team_scope
        )
        
        logger.info(f"Total epics received from API: {len(epics_response)}")

        
        # Add due date history, labels and maturity to epics
        logger.info(f"Adding due date history, labels and maturity to {len(epics_response)} epics...")
        for i, epic in enumerate(epics_response, 1):
            issue_key = epic.get('source_issue_key')
            if issue_key:
                logger.info(f"  [{i}/{len(epics_response)}] Fetching due date history, labels and maturity for epic {issue_key}...")
                try:
                    epic['date_history'] = self.jira.get_due_date_history(issue_key)
                    epic['labels'] = self.jira.get_issue_labels(issue_key)
                    epic['maturity'] = self.jira.get_issue_maturity(issue_key) or 'N/A'

                    # Display and formatting for epics
                    current_due = (
                        epic.get('target_date')           # common in your codebase
                        or epic.get('due_date')           # fallback if present
                        or epic.get('current_due_date')   # last-resort naming
                    )
                    if current_due:
                        text, fmt = format_due_epic(current_due, epic.get('date_history') or [])
                    else:
                        text, fmt = ("N/A", [])
                    epic['due_tape_text'] = text
                    epic['due_tape_fmt'] = fmt
                     
                    logger.info(f"  [{i}/{len(epics_response)}] ✓ Due date history, labels and maturity fetched for {issue_key}")
                except Exception as e:
                    logger.warning(f"  [{i}/{len(epics_response)}] ✗ Error fetching due date history, labels and maturity for {issue_key}: {e}")
                    epic['date_history'] = []
                    epic['labels'] = []
                    epic['maturity'] = 'N/A'
            else:
                logger.info(f"  [{i}/{len(epics_response)}] No issue key for epic, skipping due date history and labels")
                epic['date_history'] = []
                epic['labels'] = []
                epic['maturity'] = 'N/A'
        
        logger.info(f"Due date history, labels and maturity level processing completed for epics")
        
        filtered_epics, excluded_epics = filter_items(epics_response, lookback_start, lookback_end)
        logger.info(f"Epics after filtering: {len(filtered_epics)}")
        
        logger.info(f"Total items to include in report: {len(filtered_deliverables) + len(filtered_epics)}")
        
        # Determine slide ID
        slide_id = team_config.get('slide_id')
        if slide_id and slide_id.startswith('id.'):
            slide_id = slide_id[3:]
            logger.info(f"Stripped 'id.' prefix from slide ID: {slide_id}")

        if slide_id:
            logger.info(f"Using existing slide ID: {slide_id}")
        else:
            logger.info("No slide ID provided - creating new slide")
            slide_id = self.slides.create_slide()
            if slide_id:
                logger.info(f"NEW SLIDE CREATED: {slide_id} - Please add this to teams_config.yaml for team {team_identifier}")
            else:
                logger.error(f"Error: Failed to create new slide for team {team_identifier}")
                return

        # Define stable ids for Risks widgets
        risks_title_oid   = f"risks_title_{team_identifier}"
        risks_content_oid = f"risks_content_{team_identifier}"

        # Read existing text before any clearing
        existing_risks_text = ""
        try:
            existing_risks_text = self.slides.get_shape_text(slide_id, risks_content_oid)
            if existing_risks_text:
                logger.info("Read existing Risks/Mitigations text (will restore if needed).")
        except Exception as e:
            logger.warning(f"Warning: could not read existing risks text: {e}")

        # Selective clear that preserves the manual input box if it exists
        try:
            preserve_ids = []
            if self.slides.shape_exists(slide_id, risks_content_oid):
                preserve_ids.append(risks_content_oid)
            self.slides.clear_slide_content(slide_id, preserve_object_ids=preserve_ids)
        except Exception as e:
            logger.warning(f"Warning: Could not clear slide content: {e}")
            logger.info("Slide may not exist - creating new slide...")
            slide_id = self.slides.create_slide()
            if not slide_id:
                logger.error(f"Error: Failed to create new slide for team {team_identifier}")
                return
            
        # --- Clean up the team name for display ---
        raw_name = team_config['team_name']
        trimmed_name = raw_name.removeprefix("[PRD] ")
        parts = trimmed_name.split(":", 1)
        display_name = parts[0].strip()
        self.jellyfish.team_name = display_name

        # Include the team's EM and domain
        presenter = team_config.get("presenter", "Presenter")
        presenter_name = presenter.split()[0] if presenter else "Presenter" 
        domain = team_config.get('domain', '') or ''
        domain = domain.strip()

        # Build title: include domain only if non-empty
        if domain:
            title_text = f"{self.jellyfish.team_name} - {presenter_name} - {domain}"
        else:
            title_text = f"{self.jellyfish.team_name} - {presenter_name}"

        # Add title to slide
        self.slides.add_title(slide_id, title_text, 50, 20)
        
        # Get formatted due dates with history for all items

        deliverable_keys = {
            d.get('source_issue_key')
            for d in (filtered_deliverables or [])
            if d.get('source_issue_key')
        }

        # Reuse the already-fetched histories so we don't re-call Jira here
        _date_histories = {}
        for _it in (filtered_deliverables or []) + (filtered_epics or []):
            _k = _it.get('source_issue_key')
            if _k:
                _date_histories[_k] = _it.get('date_history') or []

        def get_formatted_due_date(current_date: str, issue_key: str):
            if not current_date:
                return ("N/A", [])
            history = _date_histories.get(issue_key, [])

            # Deliverables: last 2 (previous struck, current clean)
            if issue_key in deliverable_keys:
                return format_due_deliv(current_date, history)

            # Epics (default): last 4 (previous 3 struck, current clean)
            return format_due_epic(current_date, history)
        merged_data, formatting_map, color_map, merge_map, link_map = prepare_merged_table(
            filtered_deliverables, 
            filtered_epics,
            get_formatted_due_date
        )
        
        y_position = 80
        logger.info(f"Merged table data: {len(merged_data)} rows")

        merged_data, formatting_map, color_map, merge_map, link_map = prepare_merged_table(
            filtered_deliverables,
            filtered_epics,
            get_formatted_due_date,
        )
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
            logger.error("Error: Failed to create table")
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
        RISKS_CONTENT_FONT_SIZE = 10
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

        # --- Risks/Mitigations Title (safe to recreate each run) ---
        if not self.slides.shape_exists(slide_id, risks_title_oid):
            self.slides.add_text_box(
                slide_id,
                "Risks / Mitigations",
                risks_title_x,
                risks_title_y,
                text_box_width,
                RISKS_TITLE_HEIGHT,
                font_size=RISKS_TITLE_FONT_SIZE,
                object_id=risks_title_oid
        )
        else:
            # Optionally: keep position consistent if the slide layout shifted
            self.slides.service.presentations().batchUpdate(
                presentationId=self.slides.presentation_id,
                body={"requests": [{
                    "updatePageElementTransform": {
                        "objectId": risks_title_oid,
                        "applyMode": "ABSOLUTE",
                    "transform": {
                        "scaleX": 1, "scaleY": 1, "shearX": 0, "shearY": 0,
                        "translateX": risks_title_x, "translateY": risks_title_y, "unit": "PT"
                    }
                }
            }, {
                    "updatePageElementAltText": {  # harmless no-op to keep API happy if needed
                        "objectId": risks_title_oid,
                        "title": "Risks / Mitigations"
                }
            }]}
            ).execute()
        self.slides.update_textbox_style(risks_title_oid, font_size=RISKS_TITLE_FONT_SIZE, bold=True)

        # --- Risks/Mitigations Content Box (manual input that must persist) ---
                # --- Risks/Mitigations Content Box (manual input that must persist) ---
        def _normalize_text(s: str) -> str:
            if not s:
                return ""
            # Strip whitespace and zero-width chars that Slides sometimes leaves behind
            return "".join(ch for ch in s.strip() if ch not in ("\u200b", "\ufeff"))

        # 1) Try to read any existing text (in case we need to recreate it)
        existing_risks_text = ""
        try:
            existing_risks_text = self.slides.get_shape_text(slide_id, risks_content_oid) or ""
        except Exception as e:
            logger.warning(f"Warn: could not read risks text: {e}")
        existing_risks_text_norm = _normalize_text(existing_risks_text)

        if not self.slides.shape_exists(slide_id, risks_content_oid):
            # First run (or the box was deleted): create it with previous text if available, else "- "
            initial_text = existing_risks_text if existing_risks_text_norm else RISKS_CONTENT_INITIAL_TEXT
            self.slides.add_bordered_text_box(
                slide_id,
                initial_text,
                risks_content_x,
                risks_content_y,
                width=text_box_width,
                height=RISKS_CONTENT_HEIGHT,
                border_color=RISKS_CONTENT_BORDER_COLOR,
                border_weight=RISKS_CONTENT_BORDER_WEIGHT,
                font_size=RISKS_CONTENT_FONT_SIZE,
                object_id=risks_content_oid
            )
            self.slides.update_textbox_style(risks_content_oid, font_size=RISKS_CONTENT_FONT_SIZE, bold=False)
        else:
            # Box already exists. Do not overwrite user text.
            # Optionally: keep position/size consistent if your table width changed.
            requests = [
                {
                    "updatePageElementTransform": {
                        "objectId": risks_content_oid,
                        "applyMode": "ABSOLUTE",
                        "transform": {
                            "scaleX": 1, "scaleY": 1, "shearX": 0, "shearY": 0,
                            "translateX": risks_content_x, "translateY": risks_content_y, "unit": "PT"
                        }
                    }
                },
                # Ensure border exists/looks right (idempotent)
                {
                    "updateShapeProperties": {
                        "objectId": risks_content_oid,
                        "shapeProperties": {
                            "outline": {
                                "outlineFill": {
                                    "solidFill": {"color": {"rgbColor": RISKS_CONTENT_BORDER_COLOR}}
                                },
                                "weight": {"magnitude": RISKS_CONTENT_BORDER_WEIGHT, "unit": "PT"}
                            }
                        },
                        "fields": "outline"
                    }
                }
            ]

            if existing_risks_text_norm == "":
                # Seed the empty box so downstream code won't choke on styling empty runs
                # Note: Do NOT call deleteText on an empty shape (Slides 400 error). Just insert.
                requests.extend([
                    {"insertText": {"objectId": risks_content_oid, "insertionIndex": 0, "text": RISKS_CONTENT_INITIAL_TEXT}}
                ])
                logger.info("Risks/Mitigations text box was empty. Seeded with '- ' to keep script running.")

            self.slides.service.presentations().batchUpdate(
                presentationId=self.slides.presentation_id,
                body={"requests": requests}
            ).execute()
            self.slides.update_textbox_style(risks_content_oid, font_size=RISKS_CONTENT_FONT_SIZE, bold=False)
            logger.info("Preserved existing Risks/Mitigations content box and its text.")

            self.slides.update_textbox_style(risks_content_oid, font_size=RISKS_CONTENT_FONT_SIZE, bold=False)
            logger.info("Preserved existing Risks/Mitigations content box and its text.")
                
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
            logger.info(f"Added exclusion log with {len(all_excluded_items)} items")
            
        logger.info(f"Slide generated for team {team_identifier}")
    
    def generate_slides(self):
        """Generate Google Slides status reports based on team selection"""
        if self.team_selection == 'all':
            logger.info("Generating slides for all teams...")
            all_teams = get_all_teams(self.teams_config)
                
            for team_identifier, team_config in all_teams:
                self.generate_slide_for_team(team_identifier, team_config)
                
            logger.info(f"\nCompleted generating slides for all teams")
        else:
            # Generate slide for specific team
            team_config = get_team_config(self.teams_config, self.team_selection)
            if team_config:
                    self.generate_slide_for_team(self.team_selection, team_config)
                    logger.info(f"\nCompleted generating slide for team {self.team_selection}")
            else:
                    logger.error(f"Error: Team '{self.team_selection}' not found in teams configuration")
                    logger.info("Available teams:")
                    all_teams = get_all_teams(self.teams_config)
                    for team_id, _ in all_teams:
                        logger.info(f"  - {team_id}")

def main():
    """Main entry point"""
    try:
        parser = argparse.ArgumentParser(description='Generate Jellyfish status report')
        parser.add_argument('--config', required=True, help='Path to config file')
        parser.add_argument('--team', help='Team identifier (e.g., BBEE, TOL, CLIP) or "all" for all teams')
        args = parser.parse_args()
        logger.debug(f"Set args: {args}")
        
        config = load_config(args.config)
        logger.info("Loaded config: %s", os.path.abspath(args.config))
        logger.info("google_slides section: %s", config.get("google_slides"))
        logger.info("presentation_id seen: %s", config.get("google_slides", {}).get("presentation_id"))

        if args.team:
            config['team_selection'] = args.team
            logger.debug(f"Updated config['team_selection']: {config['team_selection']}")

        generator = StatusReportGenerator(config)
        logger.debug(f"Set generator: {generator}")
        generator.run()
        logger.info("Ran generator.run()")
        logger.debug("Completed: main - main.py")
    except Exception as e:
        logger.exception("Unhandled exception in main()")
        raise

if __name__ == '__main__':
    main()