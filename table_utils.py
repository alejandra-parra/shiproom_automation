"""
Table utility functions for the Jellyfish Status Report Generator.
This module handles the preparation and formatting of tables for the status report.
"""

from typing import List, Dict, Tuple, Callable
from status_utils import get_status_color

def prepare_deliverables_table(
    deliverables: List[Dict],
    due_formatter: Callable[[str, str], Tuple[str, list]]
) -> Tuple[List[List], Dict, Dict, Dict]:
    rows = []
    formatting_map = {}
    color_map = {}
    link_map = {}

    for row_idx, item in enumerate(deliverables):
        issue_key = item.get('source_issue_key', '')
        issue_url = item.get('source_issue_url', '')

        due_date_display, formatting_instructions = due_formatter(
            item.get('target_date', ''),
            issue_key
        )

        name = item.get('name', '')
        maturity = item.get('maturity', 'N/A')
        status = item.get('_status', 'In Progress')

        rows.append([
            issue_key,
            name,
            maturity,
            due_date_display,
            ''
        ])

        # Map date cell (row_idx, 3) to strikethrough ranges
        if formatting_instructions:
            formatting_map[(row_idx + 1, 3)] = formatting_instructions  # +1 if you have a header row before this block
        # Status colour
        status_color = get_status_color(status)
        if status_color:
            color_map[(row_idx + 1, 4)] = status_color   # +1 because of the Deliverables header row
        
        # Issue key hyperlink
        if issue_url:
            link_map[(row_idx + 1, 0)] = issue_url
    
    return rows, formatting_map, color_map, link_map

def prepare_epics_table(epics: List[Dict], due_formatter: Callable[[str, str], Tuple[str, list]]) -> Tuple[List[List], Dict, Dict, Dict]:
    """Prepare epics data for table rendering, including a map of (row, col) to issue key URLs."""
    rows = []
    formatting_map = {}  # (row, col) -> formatting instructions
    color_map = {}      # (row, col) -> background color
    link_map = {}       # (row, col) -> URL for issue key
    
    for row_idx, item in enumerate(epics):
        issue_key = item.get('source_issue_key', '')
        issue_url = item.get('source_issue_url', '')
        due_date_display, formatting_instructions = due_formatter(
            item.get('target_date', ''), 
            issue_key
        )
        
        name = item.get('name', '')
        status = item.get('_status', 'In Progress')
        
        # Use plain text issue key
        row = [
            issue_key,  # Issue key (to be hyperlinked)
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
        
        # Store link for issue key (column 0)
        if issue_url:
            link_map[(row_idx + 1, 0)] = issue_url  # +1 for header
    
    return rows, formatting_map, color_map, link_map

def prepare_merged_table(deliverables: List[Dict], epics: List[Dict], due_formatter: Callable[[str,str],Tuple [str,list]]) -> Tuple[List[List], Dict, Dict, list, Dict]:
    """Prepare merged table data for both deliverables and epics, including a link_map for issue key hyperlinks."""
    rows = []
    formatting_map = {}  # (row, col) -> formatting instructions
    color_map = {}      # (row, col) -> background color
    merge_map = []      # List of cell merge instructions
    link_map = {}       # (row, col) -> URL for issue key

    # --- Deliverables Section ---
    # Add header row with all column titles
    deliverables_header_row = ["Deliverable", "Name", "Maturity", "Due Date", "Status"]
    rows.append(deliverables_header_row)
    # Black background, bold white text for Deliverables header
    for col in range(5):
        formatting_map[(0, col)] = [{"bold": True, "fontSize": 10, "foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0}}]
        color_map[(0, col)] = {"red": 0.0, "green": 0.0, "blue": 0.0}

    deliverables_rows, deliverables_formatting, deliverables_colors, deliverables_links = prepare_deliverables_table(deliverables, due_formatter)
    for i, row in enumerate(deliverables_rows):
        row_idx = len(rows)
        rows.append(row)
        for key, val in deliverables_formatting.items():
            if key[0] == i + 1:
                formatting_map[(row_idx, key[1])] = val
        for key, val in deliverables_colors.items():
            if key[0] == i + 1:
                color_map[(row_idx, key[1])] = val
        for key, val in deliverables_links.items():
            if key[0] == i + 1:
                link_map[(row_idx, key[1])] = val

    # --- Epics Section ---
    if epics:
        # Spacer row (invisible) - will be merged across all columns
        spacer_row = ["", "", "", "", ""]
        spacer_row_idx = len(rows)
        rows.append(spacer_row)
        # Merge spacer row across all columns
        merge_map.append({"row": spacer_row_idx, "col": 0, "rowSpan": 1, "colSpan": 5, "is_spacer": True})

        # Epics header row with all column titles
        epics_header_row = ["Epics", "Name", "", "Due Date", "Status"]
        row_idx = len(rows)
        rows.append(epics_header_row)
        # Jira epic purple: #8777D9
        epic_purple = {"red": 135/255, "green": 119/255, "blue": 217/255}
        for col in range(5):
            formatting_map[(row_idx, col)] = [{"bold": True, "fontSize": 10, "foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0}}]
            color_map[(row_idx, col)] = epic_purple
        # Merge Name cell with empty cell in header row
        merge_map.append({"row": row_idx, "col": 1, "rowSpan": 1, "colSpan": 2})

        epics_rows, epics_formatting, epics_colors, epics_links = prepare_epics_table(epics, due_formatter)
        for i, epic_row in enumerate(epics_rows):
            row_idx = len(rows)
            rows.append([
                epic_row[0],  # Epic Link
                epic_row[1],  # Name
                '',  # Empty maturity (for spanning)
                epic_row[2],  # Due Date
                epic_row[3]   # Status
            ])
            # Merge Name+Maturity columns for epics
            merge_map.append({"row": row_idx, "col": 1, "rowSpan": 1, "colSpan": 2})
            for key, val in epics_formatting.items():
                if key[0] == i + 1:
                    formatting_map[(row_idx, 3)] = val
            for key, val in epics_colors.items():
                if key[0] == i + 1:
                    color_map[(row_idx, 4)] = val
            for key, val in epics_links.items():
                if key[0] == i + 1:
                    link_map[(row_idx, 0)] = val

    return rows, formatting_map, color_map, merge_map, link_map 