#!/usr/bin/env python3
"""
Jellyfish Status Report Generator
Generates Google Sheets status reports for engineering teams based on Jellyfish data
"""

import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import json
import argparse
import yaml
from pathlib import Path
from jira import JIRA
import os
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from clients.google_slides import GoogleSlidesClient
from clients.jira import JiraClient
from clients.jellyfish import JellyfishClient
from config.config_loader import load_config
from utils.date_utils import format_date, get_report_date_range
from utils.table_utils import prepare_merged_table
from utils.filter_utils import filter_items
from utils.due_date_utils import format_due_date_with_history
from utils.status_utils import STATUS_MAPPING

# Load environment variables
load_dotenv()

class GoogleSlidesClient:
    """Client for interacting with Google Slides API"""
    
    def __init__(self, config: Dict):
        # Get credentials from environment - support both file path and JSON content
        service_account_file = os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE')
        service_account_json = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
        
        if not service_account_file and not service_account_json:
            raise ValueError("Either GOOGLE_SERVICE_ACCOUNT_FILE or GOOGLE_SERVICE_ACCOUNT_JSON environment variable must be set")
        
        # Define the scope
        scopes = ['https://www.googleapis.com/auth/presentations']
        
        # Create credentials
        if service_account_json:
            # Parse JSON from environment variable
            import json
            try:
                service_account_info = json.loads(service_account_json)
            except json.JSONDecodeError as e:
                print(f"JSON parsing error: {e}")
                print("Attempting to fix JSON formatting issues...")
                
                # Fix common JSON issues:
                # 1. Replace actual newlines with escaped newlines
                # 2. Fix any other control characters
                fixed_json = service_account_json
                
                # Replace actual newlines in the JSON with escaped newlines
                fixed_json = fixed_json.replace('\n', '\\n')
                fixed_json = fixed_json.replace('\r', '\\r')
                fixed_json = fixed_json.replace('\t', '\\t')
                
                try:
                    service_account_info = json.loads(fixed_json)
                    print("Successfully fixed JSON formatting")
                except json.JSONDecodeError as e2:
                    print(f"Could not fix JSON automatically: {e2}")
                    print("Please check your .env file and ensure the JSON is properly formatted.")
                    raise
            self.credentials = Credentials.from_service_account_info(
                service_account_info, scopes=scopes
            )
            print("Using Google Service Account from JSON content in environment variable")
        else:
            # Use file path
            self.credentials = Credentials.from_service_account_file(
                service_account_file, scopes=scopes
            )
            print(f"Using Google Service Account from file: {service_account_file}")
        
        # Build the service with timeout
        import socket
        socket.setdefaulttimeout(30)  # 30 second timeout
        self.service = build('slides', 'v1', credentials=self.credentials)
        
        # Get presentation ID and slide ID from config
        self.presentation_id = config.get('google_slides', {}).get('presentation_id')
        if not self.presentation_id:
            raise ValueError("Google Presentation ID not found in config file under 'google_slides.presentation_id'")
        
        self.slide_id = config.get('google_slides', {}).get('slide_id')
        if not self.slide_id:
            raise ValueError("Google Slide ID not found in config file under 'google_slides.slide_id'")
        
        print(f"Initialized Google Slides client with presentation ID: {self.presentation_id}")
        print(f"Will update slide ID: {self.slide_id}")
    
    def get_presentation(self):
        """Get presentation metadata"""
        try:
            print(f"Fetching presentation metadata for ID: {self.presentation_id}")
            presentation = self.service.presentations().get(
                presentationId=self.presentation_id
            ).execute()
            print("Successfully retrieved presentation metadata")
            return presentation
        except HttpError as e:
            print(f"Error getting presentation: {e}")
            raise
        except Exception as e:
            print(f"Unexpected error getting presentation: {e}")
            raise
    
    def clear_slide_content(self, slide_id: str):
        """Clear all content from a slide except the slide itself"""
        try:
            presentation = self.get_presentation()
            
            # Find the slide
            slide = None
            for s in presentation.get('slides', []):
                if s['objectId'] == slide_id:
                    slide = s
                    break
            
            if not slide:
                print(f"Slide {slide_id} not found")
                return
            
            # Collect all element IDs to delete
            delete_requests = []
            for element in slide.get('pageElements', []):
                delete_requests.append({
                    'deleteObject': {
                        'objectId': element['objectId']
                    }
                })
            
            if delete_requests:
                self.service.presentations().batchUpdate(
                    presentationId=self.presentation_id,
                    body={'requests': delete_requests}
                ).execute()
                print(f"Cleared {len(delete_requests)} elements from slide {slide_id}")
            
        except HttpError as e:
            print(f"Error clearing slide {slide_id}: {e}")
    
    def create_slide(self, slide_id: str = None):
        """Create a new slide"""
        try:
            if not slide_id:
                slide_id = f"slide_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            requests = [{
                'createSlide': {
                    'objectId': slide_id,
                    'slideLayoutReference': {
                        'predefinedLayout': 'BLANK'
                    }
                }
            }]
            
            self.service.presentations().batchUpdate(
                presentationId=self.presentation_id,
                body={'requests': requests}
            ).execute()
            
            print(f"Created slide: {slide_id}")
            return slide_id
            
        except HttpError as e:
            print(f"Error creating slide: {e}")
            raise
    
    def add_title(self, slide_id: str, title: str, x: float = 50, y: float = 50):
        """Add a title text box to a slide"""
        try:
            import time
            title_id = f"title_{int(time.time() * 1000000)}"
            
            requests = [
                {
                    'createShape': {
                        'objectId': title_id,
                        'shapeType': 'TEXT_BOX',
                        'elementProperties': {
                            'pageObjectId': slide_id,
                            'size': {
                                'height': {'magnitude': 50, 'unit': 'PT'},
                                'width': {'magnitude': 600, 'unit': 'PT'}
                            },
                            'transform': {
                                'scaleX': 1,
                                'scaleY': 1,
                                'translateX': x,
                                'translateY': y,
                                'unit': 'PT'
                            }
                        }
                    }
                },
                {
                    'insertText': {
                        'objectId': title_id,
                        'text': title
                    }
                },
                {
                    'updateTextStyle': {
                        'objectId': title_id,
                        'style': {
                            'fontSize': {'magnitude': 24, 'unit': 'PT'},
                            'bold': True
                        },
                        'fields': 'fontSize,bold'
                    }
                }
            ]
            
            self.service.presentations().batchUpdate(
                presentationId=self.presentation_id,
                body={'requests': requests}
            ).execute()
            
            print(f"Added title to slide {slide_id}")
            
        except HttpError as e:
            print(f"Error adding title to slide {slide_id}: {e}")
    
    def get_table_dimensions(self, table_id: str) -> Dict:
        """Get actual table dimensions after creation"""
        try:
            print(f"Getting dimensions for table: {table_id}")
            presentation = self.get_presentation()
            
            # First, find our target slide
            target_slide = None
            for slide in presentation.get('slides', []):
                if slide.get('objectId') == self.slide_id:
                    target_slide = slide
                    print(f"Found target slide: {self.slide_id}")
                    break
            
            if not target_slide:
                print(f"Target slide {self.slide_id} not found in presentation")
                return {}
            
            # Now look for our table in the target slide
            for element in target_slide.get('pageElements', []):
                element_id = element.get('objectId', '')
                if element_id == table_id:
                    print(f"Found table element: {table_id}")
                    size = element.get('size', {})
                    transform = element.get('transform', {})
                    
                    # Check if we have the expected data structure
                    if not size or not transform:
                        print(f"Missing size or transform data for table {table_id}")
                        return {}
                    
                    # Google Slides API returns dimensions in EMU (English Metric Units)
                    # 1 point = 12,700 EMUs
                    height_emu = size.get('height', {}).get('magnitude', 0)
                    width_emu = size.get('width', {}).get('magnitude', 0)
                    y_emu = transform.get('translateY', 0)
                    x_emu = transform.get('translateX', 0)
                    
                    print(f"Raw EMU dimensions for table {table_id}:")
                    print(f"  Height: {height_emu} EMU")
                    print(f"  Width: {width_emu} EMU")
                    print(f"  Y position: {y_emu} EMU")
                    print(f"  X position: {x_emu} EMU")
                    
                    # Convert EMU to points (1 point = 12,700 EMUs)
                    height_pt = height_emu / 12700
                    width_pt = width_emu / 12700
                    y_pt = y_emu / 12700
                    x_pt = x_emu / 12700
                    
                    print(f"Converted to points for table {table_id}:")
                    print(f"  Height: {height_pt:.2f} PT")
                    print(f"  Width: {width_pt:.2f} PT")
                    print(f"  Y position: {y_pt:.2f} PT")
                    print(f"  X position: {x_pt:.2f} PT")
                    
                    dimensions = {
                        'height': height_pt,
                        'width': width_pt,
                        'y_position': y_pt,
                        'x_position': x_pt
                    }
                    
                    return dimensions
                else:
                    print(f"Found element: {element_id} (not our table)")
            
            print(f"Table {table_id} not found in slide {self.slide_id}")
            return {}
        except Exception as e:
            print(f"Error getting table dimensions for {table_id}: {e}")
            import traceback
            traceback.print_exc()
            return {}

    def add_table(self, slide_id: str, data: List[List], x: float = 50, y: float = 120, formatting_map: Dict = None, color_map: Dict = None, header_color: Dict = None, merge_map: List[Dict] = None):
        """Add a table to a slide"""
        try:
            # Use microseconds for unique table ID
            import time
            table_id = f"table_{int(time.time() * 1000000)}"
            
            if not data:
                print("No data to add to table")
                return None, None
            
            rows = len(data)
            cols = len(data[0]) if data else 0
            
            if rows == 0 or cols == 0:
                print("Invalid table dimensions")
                return None, None
            
            # Define column widths based on content type
            # For deliverables: [Key, Name, Maturity, Due Date, Status]
            # For epics: [Key, Name, Due Date, Status]
            if cols == 5:  # Deliverables table
                column_widths = [80, 250, 60, 100, 60]  # Key, Name, Maturity, Due Date, Status
            elif cols == 4:  # Epics table
                column_widths = [80, 280, 100, 60]  # Key, Name, Due Date, Status
            else:
                # Fallback to equal widths
                column_widths = [140] * cols
            
            total_width = sum(column_widths)
            
            # Calculate initial height based on number of rows
            # Each row is 25pt high, plus 20pt for padding
            initial_height = rows * 25 + 20
            
            # Step 1: Create table first
            create_table_request = {
                'createTable': {
                    'objectId': table_id,
                    'elementProperties': {
                        'pageObjectId': slide_id,
                        'size': {
                            'height': {'magnitude': initial_height, 'unit': 'PT'},
                            'width': {'magnitude': total_width, 'unit': 'PT'}
                        },
                        'transform': {
                            'scaleX': 1,
                            'scaleY': 1,
                            'translateX': x,
                            'translateY': y,
                            'unit': 'PT'
                        }
                    },
                    'rows': rows,
                    'columns': cols
                }
            }
            
            # Create the table first
            self.service.presentations().batchUpdate(
                presentationId=self.presentation_id,
                body={'requests': [create_table_request]}
            ).execute()
            
            print(f"Created table {table_id}")
            
            # Small delay to ensure table is fully created
            import time
            time.sleep(0.5)
            
            # Step 1.5: Set column widths
            column_width_requests = []
            for col_idx, width in enumerate(column_widths):
                column_width_requests.append({
                    'updateTableColumnProperties': {
                        'objectId': table_id,
                        'columnIndices': [col_idx],
                        'tableColumnProperties': {
                            'columnWidth': {
                                'magnitude': width,
                                'unit': 'PT'
                            }
                        },
                        'fields': 'columnWidth'
                    }
                })
            
            if column_width_requests:
                self.service.presentations().batchUpdate(
                    presentationId=self.presentation_id,
                    body={'requests': column_width_requests}
                ).execute()
                print(f"Set column widths: {column_widths}")
            
            # Step 2: Add content to all cells in one batch
            all_cell_requests = []
            for row_idx, row in enumerate(data):
                for col_idx, cell_value in enumerate(row):
                    # Use the correct cell location format
                    cell_location = {
                        'rowIndex': row_idx,
                        'columnIndex': col_idx
                    }
                    # Add text to cell
                    all_cell_requests.append({
                        'insertText': {
                            'objectId': table_id,
                            'cellLocation': cell_location,
                            'text': str(cell_value) if cell_value else '',
                            'insertionIndex': 0
                        }
                    })
                    # Set font size for all cells that have text
                    if cell_value and str(cell_value).strip():
                        all_cell_requests.append({
                            'updateTextStyle': {
                                'objectId': table_id,
                                'cellLocation': cell_location,
                                'style': {
                                    'fontSize': {'magnitude': 7, 'unit': 'PT'}
                                },
                                'textRange': {
                                    'type': 'ALL'
                                },
                                'fields': 'fontSize'
                            }
                        })
                    # Format header row
                    if row_idx == 0:
                        # Use custom header color if provided, otherwise default gray
                        if header_color:
                            header_bg_color = header_color
                            text_color = {'red': 1.0, 'green': 1.0, 'blue': 1.0}  # White text
                        else:
                            header_bg_color = {'red': 0.8, 'green': 0.8, 'blue': 0.8}  # Gray
                            text_color = {'red': 0.0, 'green': 0.0, 'blue': 0.0}  # Black text
                        # Only apply text style if cell has text
                        if cell_value and str(cell_value).strip():
                            all_cell_requests.append({
                                'updateTextStyle': {
                                    'objectId': table_id,
                                    'cellLocation': cell_location,
                                    'style': {
                                        'bold': True,
                                        'fontSize': {'magnitude': 7, 'unit': 'PT'},
                                        'foregroundColor': {
                                            'opaqueColor': {
                                                'rgbColor': text_color
                                            }
                                        }
                                    },
                                    'textRange': {
                                        'type': 'ALL'
                                    },
                                    'fields': 'bold,fontSize,foregroundColor'
                                }
                            })
                        all_cell_requests.append({
                            'updateTableCellProperties': {
                                'objectId': table_id,
                                'tableRange': {
                                    'location': cell_location,
                                    'rowSpan': 1,
                                    'columnSpan': 1
                                },
                                'tableCellProperties': {
                                    'tableCellBackgroundFill': {
                                        'solidFill': {
                                            'color': {
                                                'rgbColor': header_bg_color
                                            }
                                        }
                                    }
                                },
                                'fields': 'tableCellBackgroundFill'
                            }
                        })
            
            # Execute all cell requests at once
            if all_cell_requests:
                self.service.presentations().batchUpdate(
                    presentationId=self.presentation_id,
                    body={'requests': all_cell_requests}
                ).execute()
            
            # Apply strikethrough formatting if provided
            if formatting_map:
                formatting_requests = []
                for (row_idx, col_idx), instructions in formatting_map.items():
                    # Only apply formatting if the cell contains text
                    cell_text = ''
                    if 0 <= row_idx < len(data) and 0 <= col_idx < len(data[row_idx]):
                        cell_text = str(data[row_idx][col_idx])
                    if not cell_text.strip():
                        continue
                    cell_location = {
                        'rowIndex': row_idx,
                        'columnIndex': col_idx
                    }
                    for instruction in instructions:
                        # Support both strikethrough and other styles
                        style = {}
                        if 'strikethrough' in instruction:
                            style['strikethrough'] = instruction['strikethrough']
                        if 'bold' in instruction:
                            style['bold'] = instruction['bold']
                        if 'fontSize' in instruction:
                            style['fontSize'] = {'magnitude': 7, 'unit': 'PT'}
                        if 'foregroundColor' in instruction:
                            style['foregroundColor'] = {'opaqueColor': {'rgbColor': instruction['foregroundColor']}}
                        if not style:
                            continue
                        formatting_requests.append({
                            'updateTextStyle': {
                                'objectId': table_id,
                                'cellLocation': cell_location,
                                'style': style,
                                'textRange': {
                                    'type': 'ALL' if 'strikethrough' not in instruction else 'FIXED_RANGE',
                                    'startIndex': instruction.get('start', 0),
                                    'endIndex': instruction.get('end', 0)
                                } if 'strikethrough' in instruction else {'type': 'ALL'},
                                'fields': ','.join(style.keys())
                            }
                        })
                if formatting_requests:
                    self.service.presentations().batchUpdate(
                        presentationId=self.presentation_id,
                        body={'requests': formatting_requests}
                    ).execute()
                    print(f"Applied formatting to {len(formatting_requests)} text ranges")

            # Apply background colors if provided
            if color_map:
                color_requests = []
                for (row_idx, col_idx), color in color_map.items():
                    cell_location = {
                        'rowIndex': row_idx,
                        'columnIndex': col_idx
                    }
                    color_requests.append({
                        'updateTableCellProperties': {
                            'objectId': table_id,
                            'tableRange': {
                                'location': cell_location,
                                'rowSpan': 1,
                                'columnSpan': 1
                            },
                            'tableCellProperties': {
                                'tableCellBackgroundFill': {
                                    'solidFill': {
                                        'color': {
                                            'rgbColor': color
                                        }
                                    }
                                }
                            },
                            'fields': 'tableCellBackgroundFill'
                        }
                    })
                if color_requests:
                    self.service.presentations().batchUpdate(
                        presentationId=self.presentation_id,
                        body={'requests': color_requests}
                    ).execute()
                    print(f"Applied background colors to {len(color_requests)} cells")

            # --- Handle merged cells and custom background/border for merged cells ---
            if merge_map:
                merge_requests = []
                border_requests = []
                for merge in merge_map:
                    # Use mergeTableCells for merging cells in Google Slides
                    merge_requests.append({
                        'mergeTableCells': {
                            'objectId': table_id,
                            'tableRange': {
                                'location': {'rowIndex': merge['row'], 'columnIndex': merge['col']},
                                'rowSpan': merge.get('rowSpan', 1),
                                'columnSpan': merge.get('colSpan', 1)
                            }
                        }
                    })
                    # If this is the spacer row, set its borders to transparent
                    is_spacer_row = merge.get('rowSpan', 1) == 1 and merge.get('colSpan', 1) == 5 and merge.get('col', 0) == 0
                    if is_spacer_row:
                        for side in ['TOP', 'BOTTOM', 'LEFT', 'RIGHT']:
                            border_requests.append({
                                'updateTableBorderProperties': {
                                    'objectId': table_id,
                                    'tableBorderProperties': {
                                        'tableBorderFill': {
                                            'solidFill': {
                                                'color': {
                                                    'rgbColor': {'red': 1.0, 'green': 1.0, 'blue': 1.0}
                                                }
                                            }
                                        },
                                        'weight': {'magnitude': 1, 'unit': 'PT'}
                                    },
                                    'tableRange': {
                                        'location': {'rowIndex': merge['row'], 'columnIndex': merge['col']},
                                        'rowSpan': 1,
                                        'columnSpan': 5
                                    },
                                    'borderPosition': side,
                                    'fields': '*'
                                }
                            })
                        # Set the bottom border of the row above and top border of the row below to default color
                        default_border = {'red': 0.8, 'green': 0.8, 'blue': 0.8}
                        # Row above (last deliverable row)
                        if merge['row'] > 0:
                            border_requests.append({
                                'updateTableBorderProperties': {
                                    'objectId': table_id,
                                    'tableBorderProperties': {
                                        'tableBorderFill': {
                                            'solidFill': {
                                                'color': {
                                                    'rgbColor': default_border
                                                }
                                            }
                                        },
                                        'weight': {'magnitude': 1, 'unit': 'PT'}
                                    },
                                    'tableRange': {
                                        'location': {'rowIndex': merge['row'] - 1, 'columnIndex': 0},
                                        'rowSpan': 1,
                                        'columnSpan': 5
                                    },
                                    'borderPosition': 'BOTTOM',
                                    'fields': '*'
                                }
                            })
                        # Row below (epics header)
                        border_requests.append({
                            'updateTableBorderProperties': {
                                'objectId': table_id,
                                'tableBorderProperties': {
                                    'tableBorderFill': {
                                        'solidFill': {
                                            'color': {
                                                'rgbColor': default_border
                                            }
                                        }
                                    },
                                    'weight': {'magnitude': 1, 'unit': 'PT'}
                                },
                                'tableRange': {
                                    'location': {'rowIndex': merge['row'] + 1, 'columnIndex': 0},
                                    'rowSpan': 1,
                                    'columnSpan': 5
                                },
                                'borderPosition': 'TOP',
                                'fields': '*'
                            }
                        })
                if merge_requests:
                    self.service.presentations().batchUpdate(
                        presentationId=self.presentation_id,
                        body={'requests': merge_requests}
                    ).execute()
                    print(f"Applied {len(merge_requests)} merged cell requests (mergeTableCells)")
                if border_requests:
                    self.service.presentations().batchUpdate(
                        presentationId=self.presentation_id,
                        body={'requests': border_requests}
                    ).execute()
                    print(f"Applied {len(border_requests)} border color requests for spacer row separation")

            print(f"Added content to table with {rows}x{cols} on slide {slide_id}")
            
            # Wait for content to be fully rendered
            time.sleep(1)
            
            # Get actual dimensions after content is added
            actual_dimensions = self.get_table_dimensions(table_id)
            if not actual_dimensions:
                # Fallback to initial dimensions if we can't get actual ones
                actual_dimensions = {
                    'height': initial_height,
                    'width': total_width,
                    'y_position': y,
                    'x_position': x
                }
            
            return table_id, actual_dimensions
            
        except HttpError as e:
            print(f"Error adding table to slide {slide_id}: {e}")
            return None, None
    
    def add_text_box(self, slide_id: str, text: str, x: float, y: float, width: float = 400, height: float = 100):
        """Add a text box to a slide"""
        try:
            import time
            text_id = f"text_{int(time.time() * 1000000)}"
            
            requests = [
                {
                    'createShape': {
                        'objectId': text_id,
                        'shapeType': 'TEXT_BOX',
                        'elementProperties': {
                            'pageObjectId': slide_id,
                            'size': {
                                'height': {'magnitude': height, 'unit': 'PT'},
                                'width': {'magnitude': width, 'unit': 'PT'}
                            },
                            'transform': {
                                'scaleX': 1,
                                'scaleY': 1,
                                'translateX': x,
                                'translateY': y,
                                'unit': 'PT'
                            }
                        }
                    }
                },
                {
                    'insertText': {
                        'objectId': text_id,
                        'text': text
                    }
                }
            ]
            
            self.service.presentations().batchUpdate(
                presentationId=self.presentation_id,
                body={'requests': requests}
            ).execute()
            
            print(f"Added text box to slide {slide_id}")
            
        except HttpError as e:
            print(f"Error adding text box to slide {slide_id}: {e}")


class JiraClient:
    """Client for interacting with Jira API to get issue history"""
    
    def __init__(self, config: Dict):
        # Get Jira credentials from environment variables only
        self.jira_url = os.getenv('JIRA_URL', '')
        self.jira_email = os.getenv('JIRA_EMAIL', '')
        self.jira_token = os.getenv('JIRA_API_TOKEN', '')
        
        if self.jira_url and self.jira_email and self.jira_token:
            self.jira = JIRA(
                server=self.jira_url,
                basic_auth=(self.jira_email, self.jira_token)
            )
            print(f"Initialized Jira client for {self.jira_url}")
        else:
            print("Warning: Jira credentials not configured. Due date history will not be available.")
            self.jira = None
    
    def get_due_date_history(self, issue_key: str) -> List[str]:
        """Get the history of due date changes for an issue in chronological order"""
        if not self.jira:
            return []
        
        try:
            # Get issue with changelog
            issue = self.jira.issue(issue_key, expand='changelog')
            
            # Get current due date
            current_due = getattr(issue.fields, 'duedate', None)
            
            # Collect all due date changes with timestamps
            changes = []
            for history in issue.changelog.histories:
                created = history.created  # Timestamp of the change
                for item in history.items:
                    if item.field.lower() in ['duedate', 'due date']:
                        changes.append({
                            'timestamp': created,
                            'from': item.fromString,
                            'to': item.toString
                        })
            
            # Sort by timestamp (oldest first)
            changes.sort(key=lambda x: x['timestamp'])
            
            # Build the chronological list of due dates
            due_dates = []
            
            if changes:
                # Start with the "from" value of the first change (if it exists)
                if changes[0]['from']:
                    due_dates.append(changes[0]['from'])
                
                # Add all the "to" values except the last one
                for change in changes[:-1]:
                    if change['to']:
                        due_dates.append(change['to'])
                
                # The current due date should be the last one (not struck through)
                if current_due:
                    due_dates.append(current_due)
                elif changes[-1]['to']:
                    # If no current due date, use the last "to" value
                    due_dates.append(changes[-1]['to'])
            else:
                # No changes found, just use current due date if it exists
                if current_due:
                    due_dates.append(current_due)
            
            return due_dates
            
        except Exception as e:
            print(f"Error getting history for {issue_key}: {e}")
            return []


class StatusReportGenerator:
    """Generates status reports from Jellyfish data"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.jellyfish = JellyfishClient(config)
        self.jira = JiraClient(config)
        self.slides = GoogleSlidesClient(config)
        self.seven_days_ago = datetime.now() - timedelta(days=7)
        self.today = datetime.now()
        
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
        filtered_deliverables = filter_items(deliverables, self.seven_days_ago, self.today)
        print(f"Fetching epics for team {self.jellyfish.team_name}...")
        epics_response = self.jellyfish.get_work_items_by_category(
            "epics",
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        )
        filtered_epics = filter_items(epics_response, self.seven_days_ago, self.today)
        slide_id = self.slides.slide_id
        try:
            self.slides.clear_slide_content(slide_id)
        except Exception as e:
            print(f"Warning: Could not clear slide content: {e}")
            print("Continuing with existing content...")
        self.slides.add_title(slide_id, f"{self.jellyfish.team_name} - Status Report", 50, 20)
        # Prepare merged table
        merged_data, formatting_map, color_map, merge_map = prepare_merged_table(
            filtered_deliverables, 
            filtered_epics,
            self.get_formatted_due_date
        )
        y_position = 80
        print(f"Merged table data: {len(merged_data)} rows")
        # Add merged table (extend add_table to support merge_map if needed)
        self.slides.add_table(
            slide_id,
            merged_data,
            50,
            y_position,
            formatting_map,
            color_map,
            None,  # header_color handled per-row in formatting_map
            merge_map=merge_map
        )
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