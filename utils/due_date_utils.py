"""
Due date utility functions for the Jellyfish Status Report Generator.
This module handles the formatting and display of due dates with their history.
Note: The current implementation shows historical dates with strikethrough formatting.
Future versions may modify how historical dates are displayed or tracked.
"""

from typing import List, Dict, Tuple
from utils.date_utils import format_date

def format_due_date_with_history(current_date: str, date_history: List[Dict]) -> Tuple[str, List[Dict]]:
    """
    Format due date with history, returning text and formatting instructions.
    
    Current implementation:
    - Shows all historical dates in sequence
    - Applies strikethrough formatting to old dates
    - Separates dates with spaces
    
    Args:
        current_date: The current due date string
        date_history: List of dicts containing due dates and their timestamps
        
    Returns:
        Tuple containing:
        - Formatted text with all dates
        - List of formatting instructions for strikethrough
    """
    if not date_history:
        # No history available, just return formatted current date
        return format_date(current_date), []
    
    # Format all dates and track formatting
    formatted_dates = []
    formatting_instructions = []
    current_pos = 0
    
    for i, date_info in enumerate(date_history):
        formatted = format_date(date_info['date'])
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