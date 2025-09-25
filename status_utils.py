"""
Status utility functions for the Jellyfish Status Report Generator.
This module handles status constants, mapping, and color definitions.
Note: The current implementation uses a simple status system with three states.
Future versions may expand the status system or modify how statuses are displayed.
"""

from typing import Dict

# Status constants
STATUS_DONE = 'Done'
STATUS_IN_PROGRESS = 'In Progress'
STATUS_OVERDUE = 'Overdue'

# Status mapping for Google Sheets
STATUS_MAPPING = {
    STATUS_DONE: STATUS_DONE,
    STATUS_IN_PROGRESS: STATUS_IN_PROGRESS,
    STATUS_OVERDUE: STATUS_OVERDUE,
    'default': STATUS_IN_PROGRESS
}

def get_status_color(status: str) -> Dict:
    """
    Get muted background color for a given status.
    
    Current color scheme:
    - Done: Muted green
    - In Progress: Muted yellow
    - Overdue: Muted red
    
    Args:
        status: The status string
        
    Returns:
        Dict containing RGB color values
    """
    colors = {
        STATUS_DONE: {
            'red': 0.8,    # Muted green
            'green': 0.9,
            'blue': 0.8
        },
        STATUS_IN_PROGRESS: {
            'red': 1.0,    # Muted yellow
            'green': 0.95,
            'blue': 0.7
        },
        STATUS_OVERDUE: {
            'red': 1.0,    # Muted red
            'green': 0.8,
            'blue': 0.8
        }
    }
    return colors.get(status, colors[STATUS_IN_PROGRESS]) 