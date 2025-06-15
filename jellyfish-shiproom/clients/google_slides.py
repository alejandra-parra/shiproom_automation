"""
Google Slides client for interacting with Google Slides API
"""

import os
import json
import socket
from datetime import datetime
from typing import List, Dict
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

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
                    return {
                        'size': size,
                        'transform': transform
                    }
            
            print(f"Table {table_id} not found in slide {self.slide_id}")
            return {}
            
        except HttpError as e:
            print(f"Error getting table dimensions: {e}")
            return {}
    
    def add_table(self, slide_id: str, data: List[List], x: float = 50, y: float = 120, formatting_map: Dict = None, color_map: Dict = None, header_color: Dict = None, merge_map: List[Dict] = None):
        """Add a table to a slide with optional formatting"""
        try:
            import time
            table_id = f"table_{int(time.time() * 1000000)}"
            
            # Calculate table dimensions
            rows = len(data)
            cols = len(data[0]) if data else 0
            
            # Create the table
            requests = [{
                'createTable': {
                    'objectId': table_id,
                    'elementProperties': {
                        'pageObjectId': slide_id,
                        'size': {
                            'height': {'magnitude': 400, 'unit': 'PT'},
                            'width': {'magnitude': 600, 'unit': 'PT'}
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
            }]
            
            # Add the data
            for row_idx, row in enumerate(data):
                for col_idx, cell in enumerate(row):
                    requests.append({
                        'insertText': {
                            'objectId': f"{table_id}_{row_idx}_{col_idx}",
                            'text': str(cell)
                        }
                    })
            
            # Apply formatting if provided
            if formatting_map:
                for cell_id, format_spec in formatting_map.items():
                    requests.append({
                        'updateTextStyle': {
                            'objectId': cell_id,
                            'style': format_spec,
                            'fields': ','.join(format_spec.keys())
                        }
                    })
            
            # Apply colors if provided
            if color_map:
                for cell_id, color in color_map.items():
                    requests.append({
                        'updateTableCellProperties': {
                            'objectId': cell_id,
                            'tableCellProperties': {
                                'tableCellBackgroundFill': {
                                    'propertyState': 'NOT_RENDERED',
                                    'solidFill': {
                                        'color': color
                                    }
                                }
                            },
                            'fields': 'tableCellBackgroundFill.solidFill.color'
                        }
                    })
            
            # Apply header color if provided
            if header_color:
                for col in range(cols):
                    cell_id = f"{table_id}_0_{col}"
                    requests.append({
                        'updateTableCellProperties': {
                            'objectId': cell_id,
                            'tableCellProperties': {
                                'tableCellBackgroundFill': {
                                    'propertyState': 'NOT_RENDERED',
                                    'solidFill': {
                                        'color': header_color
                                    }
                                }
                            },
                            'fields': 'tableCellBackgroundFill.solidFill.color'
                        }
                    })
            
            # Apply cell merging if provided
            if merge_map:
                for merge_spec in merge_map:
                    requests.append({
                        'mergeTableCells': {
                            'objectId': table_id,
                            'tableRange': merge_spec
                        }
                    })
            
            # Execute the batch update
            self.service.presentations().batchUpdate(
                presentationId=self.presentation_id,
                body={'requests': requests}
            ).execute()
            
            print(f"Added table to slide {slide_id}")
            return table_id
            
        except HttpError as e:
            print(f"Error adding table to slide {slide_id}: {e}")
            raise
    
    def add_text_box(self, slide_id: str, text: str, x: float, y: float, width: float = 400, height: float = 100):
        """Add a text box to a slide"""
        try:
            import time
            text_box_id = f"text_box_{int(time.time() * 1000000)}"
            
            requests = [
                {
                    'createShape': {
                        'objectId': text_box_id,
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
                        'objectId': text_box_id,
                        'text': text
                    }
                }
            ]
            
            self.service.presentations().batchUpdate(
                presentationId=self.presentation_id,
                body={'requests': requests}
            ).execute()
            
            print(f"Added text box to slide {slide_id}")
            return text_box_id
            
        except HttpError as e:
            print(f"Error adding text box to slide {slide_id}: {e}")
            raise 