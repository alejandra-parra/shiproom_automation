# Replace the whole function with this implementation
from typing import List, Dict, Tuple
from date_utils import format_date

def format_due_date_with_history(current_date: str, date_history: List[Dict]) -> Tuple[str, List[Dict]]:
    """
    Format due date with history, returning:
      ( full_text: str, formatting_instructions: List[Dict] )

    New behavior:
      - Show up to the last 4 due dates total (including the current one).
      - The final (most recent/current) date is NOT struck through.
      - The earlier ones are struck through.

    Arguments:
      current_date: ISO string (e.g. '2025-09-12') of the current due date.
      date_history: List of dicts describing prior due dates. We accept either:
         [{'date': 'YYYY-MM-DD'}, ...]    or    [{'value': 'YYYY-MM-DD'}, ...]
         and we will sort them ascending by date before slicing.
    """
    # Extract raw strings from history in a robust way
    raw_history = []
    for d in (date_history or []):
        if isinstance(d, dict):
            if "date" in d and d["date"]:
                raw_history.append(d["date"])
            elif "value" in d and d["value"]:
                raw_history.append(d["value"])
        elif isinstance(d, str):
            raw_history.append(d)

    # Ensure chronological order, oldest -> newest
    # (We avoid heavy parsing and rely on ISO ordering if provided.)
    raw_history = sorted(set(raw_history))  # de-dupe + sort
    max_visible_due_dates = 4

    # Build a full timeline that ends with the current date.
    # Avoid duplicating if the last history date equals current_date.
    timeline = list(raw_history)
    if not timeline or timeline[-1] != current_date:
        timeline.append(current_date)

    # Keep only the last N visible items (up to 4)
    timeline = timeline[-max_visible_due_dates:]

    # Format + assemble, applying strikethrough to all but the last one
    formatted_dates: List[str] = []
    formatting_instructions: List[Dict] = []
    current_pos = 0

    for idx, d in enumerate(timeline):
        formatted = format_date(d)
        formatted_dates.append(formatted)

        is_last = (idx == len(timeline) - 1)
        if not is_last:
            # Earlier dates are struck through
            formatting_instructions.append({
                "start": current_pos,
                "end": current_pos + len(formatted),
                "strikethrough": True
            })

        # Move cursor forward (include the space that will be added later except after the last one)
        current_pos += len(formatted)
        if not is_last:
            current_pos += 1  # for the space

    full_text = " ".join(formatted_dates)
    return full_text, formatting_instructions
