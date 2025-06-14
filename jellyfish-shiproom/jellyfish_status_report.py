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


class JellyfishClient:
    """Client for interacting with Jellyfish API"""
    
    def __init__(self, config: Dict):
        # Get Jellyfish credentials from environment variables only
        self.base_url = os.getenv('JELLYFISH_BASE_URL', '').rstrip('/')
        
        # Authorization is just the API key directly
        api_key = os.getenv('JELLYFISH_API_KEY', '')
        
        if not api_key:
            raise ValueError("JELLYFISH_API_KEY environment variable not set")
        
        if not self.base_url:
            raise ValueError("JELLYFISH_BASE_URL environment variable not set")
        
        self.headers = {
            "Authorization": "Token "+api_key,
            "accept": "application/json"
        }
        
        # Team info comes from config file
        self.team_id = config.get('team', {}).get('team_id', '')
        self.team_name = config.get('team', {}).get('team_name', '')
        
        if not self.team_id:
            raise ValueError("Jellyfish team ID not found in config file under 'team.team_id'")
        
        print(f"Initialized with base_url: {self.base_url}")
        print(f"Team ID: {self.team_id}")
        print(f"Team Name: {self.team_name}")
    
    def get_work_items_by_category(self, work_category_slug: str, 
                                   start_date: str, end_date: str) -> List[Dict]:
        """Fetch work items for a specific category (deliverable-new or epic)"""
        url = f"{self.base_url}/delivery/work_category_contents"
        params = {
            "format": "json",
            "start_date": start_date,
            "end_date": end_date,
            "unit": "week",
            "series": "true",
            "work_category_slug": work_category_slug,
            "completed_only": "false",
            "inprogress_only": "false",
            "view_archived": "false",
            "team_id": self.team_id
        }
        
        print(f"\n=== CALLING API for {work_category_slug} ===")
        print(f"URL: {url}")
        print(f"Params: {params}")
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            print(f"Response status: {response.status_code}")
            response.raise_for_status()
            data = response.json()
            
            print(f"Response type: {type(data)}")
            print(f"Response length: {len(data) if isinstance(data, list) else 'Not a list'}")
            
            # If it's empty, show that
            if not data:
                print("Response is empty!")
                return []
            
            # Extract deliverables from ONLY the last timeframe (most recent week)
            all_items = []
            if data:
                # Get only the last week's data
                last_week = data[-1]
                last_timeframe = last_week.get('timeframe', {})
                print(f"\nUsing ONLY last week: {last_timeframe.get('start')} to {last_timeframe.get('end')}")
                
                items = last_week.get('deliverables', [])
                print(f"Found {len(items)} items in last week")
                all_items = items
            
            print(f"\nTotal items to process: {len(all_items)}")
            
            # Debug: Show structure of first item
            if all_items:
                print(f"\nSample item structure:")
                first_item = all_items[0]
                print(f"Keys: {list(first_item.keys())}")
                print(f"Sample item: {json.dumps(first_item, indent=2, default=str)[:500]}...")
            
            return all_items
            
        except requests.exceptions.RequestException as e:
            print(f"ERROR: Request failed for {work_category_slug}")
            print(f"Error message: {e}")
            if hasattr(e, 'response') and e.response:
                print(f"Response status: {e.response.status_code}")
                print(f"Response text: {e.response.text[:500]}...")
            return []
        except Exception as e:
            print(f"UNEXPECTED ERROR: {type(e)} - {e}")
            return []


class StatusReportGenerator:
    """Generates status reports from Jellyfish data"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.client = JellyfishClient(config)
        self.jira_client = JiraClient(config)
        self.slides_client = GoogleSlidesClient(config)
        self.seven_days_ago = datetime.now() - timedelta(days=7)
        self.today = datetime.now()
        
        # Status mapping for Google Sheets
        self.status_mapping = {
            'Done': 'Done',
            'In Progress': 'In Progress', 
            'Overdue': 'Overdue',
            'default': 'In Progress'
        }
    
    def filter_items(self, items: List[Dict]) -> List[Dict]:
        """Filter and color-code items based on dates"""
        filtered = []
        
        for item in items:
            completed_date_str = item.get('completed_date')
            target_date_str = item.get('target_date')
            issue_key = item.get('source_issue_key', 'unknown')
            
            # Check if completed in the last week
            if completed_date_str:
                try:
                    completed_date = datetime.fromisoformat(completed_date_str.replace('Z', '+00:00'))
                    if completed_date >= self.seven_days_ago:
                        # Completed this week
                        item['_status'] = 'Done'
                        filtered.append(item)
                        print(f"{issue_key}: Completed on {completed_date_str} - Done")
                        continue
                except Exception as e:
                    print(f"Error parsing completed_date for {issue_key}: {e}")
            
            # Check if overdue (past target date)
            if target_date_str:
                try:
                    target_date = datetime.fromisoformat(target_date_str.replace('Z', '+00:00'))
                    if target_date < self.today:
                        # Past target date
                        item['_status'] = 'Overdue'
                        filtered.append(item)
                        print(f"{issue_key}: Overdue (target: {target_date_str}) - Overdue")
                        continue
                except Exception as e:
                    print(f"Error parsing target_date for {issue_key}: {e}")
            
            # Otherwise it's in progress
            item['_status'] = 'In Progress'
            filtered.append(item)
        
        return filtered
    
    def format_due_date_with_history(self, current_date: str, issue_key: str) -> Tuple[str, List[Dict]]:
        """Format due date with history, returning text and formatting instructions"""
        # Get due date history from Jira
        date_history = self.jira_client.get_due_date_history(issue_key)
        
        if not date_history:
            # No history available, just return formatted current date
            return self.format_date(current_date), []
        
        # Format all dates and track formatting
        formatted_dates = []
        formatting_instructions = []
        current_pos = 0
        
        for i, date in enumerate(date_history):
            formatted = self.format_date(date)
            if formatted:
                if i < len(date_history) - 1:
                    # This is an old date - should be struck through
                    formatting_instructions.append({
                        'start': current_pos,
                        'end': current_pos + len(formatted),
                        'strikethrough': True
                    })
                
                formatted_dates.append(formatted)
                current_pos += len(formatted)
                
                # Add space between dates (except for the last one)
                if i < len(date_history) - 1:
                    current_pos += 1  # for the space
        
        # Join all dates with spaces
        full_text = ' '.join(formatted_dates)
        return full_text, formatting_instructions
    
    def prepare_deliverables_table(self, deliverables: List[Dict]) -> Tuple[List[List], Dict, Dict]:
        """Prepare deliverables data for table rendering"""
        rows = []
        formatting_map = {}  # Maps (row, col) to formatting instructions
        color_map = {}  # Maps (row, col) to background colors
        
        for row_idx, item in enumerate(deliverables):
            issue_key = item.get('source_issue_key', '')
            due_date_display, formatting_instructions = self.format_due_date_with_history(
                item.get('target_date', ''), 
                issue_key
            )
            
            name = item.get('name', '')
            status = item.get('_status', 'In Progress')
            
            row = [
                issue_key,
                name,
                'GA',  # Default maturity
                due_date_display,
                ''  # Empty text for status - will be color-coded
            ]
            rows.append(row)
            
            # Store formatting instructions for the due date column (index 3)
            if formatting_instructions:
                formatting_map[(row_idx + 1, 3)] = formatting_instructions  # +1 because of header row
            
            # Store color for status column (index 4)
            status_color = self.get_status_color(status)
            if status_color:
                color_map[(row_idx + 1, 4)] = status_color  # +1 because of header row
        
        return rows, formatting_map, color_map
    
    def prepare_epics_table(self, epics: List[Dict]) -> Tuple[List[List], Dict, Dict]:
        """Prepare epics data for table rendering"""
        rows = []
        formatting_map = {}  # Maps (row, col) to formatting instructions
        color_map = {}  # Maps (row, col) to background colors
        
        for row_idx, item in enumerate(epics):
            issue_key = item.get('source_issue_key', '')
            due_date_display, formatting_instructions = self.format_due_date_with_history(
                item.get('target_date', ''), 
                issue_key
            )
            
            name = item.get('name', '')
            status = item.get('_status', 'In Progress')
            
            row = [
                issue_key,
                name,
                due_date_display,
                ''  # Empty text for status - will be color-coded
            ]
            rows.append(row)
            
            # Store formatting instructions for the due date column (index 2)
            if formatting_instructions:
                formatting_map[(row_idx + 1, 2)] = formatting_instructions  # +1 because of header row
            
            # Store color for status column (index 3)
            status_color = self.get_status_color(status)
            if status_color:
                color_map[(row_idx + 1, 3)] = status_color  # +1 because of header row
        
        return rows, formatting_map, color_map
    
    def get_status_color(self, status: str) -> Dict:
        """Get muted background color for status"""
        colors = {
            'Done': {
                'red': 0.8,    # Muted green
                'green': 0.9,
                'blue': 0.8
            },
            'In Progress': {
                'red': 1.0,    # Muted yellow
                'green': 0.95,
                'blue': 0.7
            },
            'Overdue': {
                'red': 1.0,    # Muted red
                'green': 0.8,
                'blue': 0.8
            }
        }
        return colors.get(status, colors['In Progress'])
    
    def format_date(self, date_str: str) -> str:
        """Format date string to YYYY-MM-DD"""
        if not date_str:
            return ''
        
        try:
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d')
        except:
            return date_str[:10] if len(date_str) >= 10 else date_str
    
    def prepare_merged_table(self, deliverables: List[Dict], epics: List[Dict]) -> Tuple[List[List], Dict, Dict, list]:
        """Prepare a single merged table with deliverables and epics, including formatting and merged cells."""
        rows = []
        formatting_map = {}  # (row, col) -> formatting instructions
        color_map = {}       # (row, col) -> background color
        merge_map = []       # List of dicts for merged cells

        # --- Deliverables Header ---
        deliverables_header = ["Deliverable", "Name", "Maturity", "Due Date", "Status"]
        rows.append(deliverables_header)
        deliverables_header_row = 0
        black_header = {'red': 0.0, 'green': 0.0, 'blue': 0.0}
        for col in range(5):
            formatting_map[(deliverables_header_row, col)] = [{"bold": True, "fontSize": 9, "foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0}}]
            color_map[(deliverables_header_row, col)] = black_header

        # --- Deliverables Rows ---
        deliverables_rows, deliverables_formatting, deliverables_colors = self.prepare_deliverables_table(deliverables)
        for i, row in enumerate(deliverables_rows):
            rows.append(row)
            # Offset formatting/color maps by +1 for header
            for key, val in deliverables_formatting.items():
                if key[0] == i + 1:
                    formatting_map[(i + 1, key[1])] = val
            for key, val in deliverables_colors.items():
                if key[0] == i + 1:
                    color_map[(i + 1, key[1])] = val

        # --- Spacer Row ---
        spacer_row_idx = len(rows)
        spacer_row = [" "] + ["" for _ in range(4)]  # Only anchor cell gets a space
        rows.append(spacer_row)
        # Merge all cells in spacer row (colSpan=5)
        merge_map.append({
            "row": spacer_row_idx,
            "col": 0,
            "rowSpan": 1,
            "colSpan": 5,
            "backgroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0},
            "noBorder": True
        })

        # --- Epics Header (Name spans columns 2 and 3) ---
        epics_header_row = len(rows)
        epics_header = ["Epic Link", "Name", "", "Due Date", "Status"]
        rows.append(epics_header)
        purple_header = {'red': 0.529, 'green': 0.467, 'blue': 0.851}
        for col in range(5):
            formatting_map[(epics_header_row, col)] = [{"bold": True, "fontSize": 9, "foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0}}]
            color_map[(epics_header_row, col)] = purple_header
        # Merge Name header (col 1+2)
        merge_map.append({
            "row": epics_header_row,
            "col": 1,
            "rowSpan": 1,
            "colSpan": 2
        })

        # --- Epics Rows (Name spans columns 2 and 3) ---
        epics_rows, epics_formatting, epics_colors = self.prepare_epics_table(epics)
        for i, epic_row in enumerate(epics_rows):
            # Insert into 5 columns: [Epic Link, Name, '', Due Date, Status], merge Name+Maturity
            row_idx = len(rows)
            row = [epic_row[0], epic_row[1], '', epic_row[2], epic_row[3]]
            rows.append(row)
            # Merge Name+Maturity columns (col 1+2)
            merge_map.append({
                "row": row_idx,
                "col": 1,
                "rowSpan": 1,
                "colSpan": 2
            })
            # Formatting and color for due date and status
            for key, val in epics_formatting.items():
                if key[0] == i + 1:
                    formatting_map[(row_idx, 3)] = val
            for key, val in epics_colors.items():
                if key[0] == i + 1:
                    color_map[(row_idx, 4)] = val

        return rows, formatting_map, color_map, merge_map

    def generate_slides(self):
        """Generate Google Slides status report with a single merged table"""
        today = datetime.now()
        start_date = today - timedelta(days=21)
        end_date = today
        print(f"Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        print(f"Fetching deliverables for team {self.client.team_name}...")
        deliverables = self.client.get_work_items_by_category(
            "deliverable-new",
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        )
        filtered_deliverables = self.filter_items(deliverables)
        print(f"Fetching epics for team {self.client.team_name}...")
        epics_response = self.client.get_work_items_by_category(
            "epics",
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        )
        filtered_epics = self.filter_items(epics_response)
        slide_id = self.slides_client.slide_id
        try:
            self.slides_client.clear_slide_content(slide_id)
        except Exception as e:
            print(f"Warning: Could not clear slide content: {e}")
            print("Continuing with existing content...")
        self.slides_client.add_title(slide_id, f"{self.client.team_name} - Status Report", 50, 20)
        # Prepare merged table
        merged_data, formatting_map, color_map, merge_map = self.prepare_merged_table(filtered_deliverables, filtered_epics)
        y_position = 80
        print(f"Merged table data: {len(merged_data)} rows")
        # Add merged table (extend add_table to support merge_map if needed)
        self.slides_client.add_table(
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


def load_config(config_path: str) -> Dict:
    """Load configuration from YAML file"""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def main():
    parser = argparse.ArgumentParser(description='Generate Jellyfish status report in Google Slides')
    parser.add_argument('--config', '-c', type=str, default='config.yaml',
                        help='Path to configuration file')
    parser.add_argument('--test-auth', action='store_true',
                        help='Test authentication with a simple API call')
    
    args = parser.parse_args()
    
    # Check if config file exists
    if not Path(args.config).exists():
        print(f"Configuration file not found: {args.config}")
        print("\nPlease create a config.yaml file. Most credentials should be in .env file.")
        print("See README.md for detailed setup instructions.")
        print("\nMinimal config.yaml structure:")
        print("""
# Required: Google Slides presentation to update
google_slides:
  presentation_id: "your-presentation-id-here"
  slide_id: "your-slide-id-here"

# Required: Team configuration
team:
  team_id: "your-team-id"
  team_name: "Your Team Name"
""")
        return
    
    # Load config
    config = load_config(args.config)
    
    # Test authentication if requested
    if args.test_auth:
        client = JellyfishClient(config)
        print("\nTesting authentication...")
        print(f"Headers: {json.dumps({k: v[:20] + '...' if k == 'Authorization' else v for k, v in client.headers.items()}, indent=2)}")
        
        # Try a simple endpoint first
        test_url = f"{client.base_url}/delivery/work_category_contents"
        print(f"\nTesting URL: {test_url}")
        
        # Try with minimal parameters
        params = {"format": "json", "team_id": client.team_id}
        response = requests.get(test_url, headers=client.headers, params=params)
        
        print(f"Response status: {response.status_code}")
        if response.status_code != 200:
            print(f"Response headers: {dict(response.headers)}")
            print(f"Response text: {response.text}")
        else:
            print("Authentication successful!")
        return
    
    # Generate report
    generator = StatusReportGenerator(config)
    generator.generate_slides()


if __name__ == "__main__":
    main()