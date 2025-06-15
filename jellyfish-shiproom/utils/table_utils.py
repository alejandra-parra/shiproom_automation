"""
Table preparation utilities for the Jellyfish Status Report Generator
"""

from typing import List, Dict, Tuple
from datetime import datetime

def get_status_color(status: str) -> Dict:
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

def prepare_deliverables_table(deliverables: List[Dict], format_due_date_with_history) -> Tuple[List[List], Dict, Dict]:
    """Prepare deliverables data for table rendering"""
    rows = []
    formatting_map = {}  # Maps (row, col) to formatting instructions
    color_map = {}  # Maps (row, col) to background colors
    
    for row_idx, item in enumerate(deliverables):
        issue_key = item.get('source_issue_key', '')
        due_date_display, formatting_instructions = format_due_date_with_history(
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
        status_color = get_status_color(status)
        if status_color:
            color_map[(row_idx + 1, 4)] = status_color  # +1 because of header row
    
    return rows, formatting_map, color_map

def prepare_epics_table(epics: List[Dict], format_due_date_with_history) -> Tuple[List[List], Dict, Dict]:
    """Prepare epics data for table rendering"""
    rows = []
    formatting_map = {}  # Maps (row, col) to formatting instructions
    color_map = {}  # Maps (row, col) to background colors
    
    for row_idx, item in enumerate(epics):
        issue_key = item.get('source_issue_key', '')
        due_date_display, formatting_instructions = format_due_date_with_history(
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
        status_color = get_status_color(status)
        if status_color:
            color_map[(row_idx + 1, 3)] = status_color  # +1 because of header row
    
    return rows, formatting_map, color_map

def prepare_merged_table(deliverables: List[Dict], epics: List[Dict], format_due_date_with_history) -> Tuple[List[List], Dict, Dict, list]:
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
    deliverables_rows, deliverables_formatting, deliverables_colors = prepare_deliverables_table(deliverables, format_due_date_with_history)
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
    epics_rows, epics_formatting, epics_colors = prepare_epics_table(epics, format_due_date_with_history)
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