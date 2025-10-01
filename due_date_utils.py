from typing import List, Dict, Tuple
from date_utils import format_date

def _normalize_iso(date_str: str) -> str:
    """
    Normalize incoming date strings to 'YYYY-MM-DD' to allow reliable comparison.
    Handles 'YYYY-MM-DD', 'YYYY-MM-DDTHH:MM:SSZ', and 'YYYY/MM/DD'.
    """
    if not date_str:
        return ""
    s = str(date_str).strip()
    if 'T' in s and len(s) >= 10:
        s = s.split('T', 1)[0]   # keep date part
    s = s.replace('/', '-')      # unify separators
    if len(s) >= 10 and s[4] == '-' and s[7] == '-':
        s = s[:10]               # YYYY-MM-DD
    return s

def _extract_history_strings(date_history: List[Dict]) -> List[str]:
    # Accepts {'date': ...}, {'value': ...}, or raw strings; de-dupes + sorts (ISO)
    raw: List[str] = []
    for d in (date_history or []):
        if isinstance(d, dict):
            if d.get("date"):
                raw.append(_normalize_iso(d["date"]))
            elif d.get("value"):
                raw.append(_normalize_iso(d["value"]))
        elif isinstance(d, str):
            raw.append(_normalize_iso(d))
    norm = [x for x in raw if x]
    return sorted(set(norm))

def _format_tape(current_date: str, history_iso: List[str], max_visible: int) -> Tuple[str, List[Dict]]:
    """
    Build the due-date tape so the current date appears exactly once at the end (unstruck),
    with up to (max_visible - 1) prior dates (struck).
    """
    cur = _normalize_iso(current_date)

    # Normalize & de-dupe history, drop any equal to current
    hist_norm = sorted(set(_normalize_iso(d) for d in (history_iso or []) if d))
    hist_norm = [d for d in hist_norm if d and d != cur]

    # Keep only last N-1 previous dates
    prev_visible = hist_norm[-max(0, max_visible - 1):] if max_visible and max_visible > 0 else []

    # Append current as the final token
    timeline = list(prev_visible)
    if cur:
        timeline.append(cur)

    # Assemble text + strikethrough ranges
    formatted_parts: List[str] = []
    fmt_instructions: List[Dict] = []
    cursor = 0
    for idx, d in enumerate(timeline):
        token = format_date(d) 
        formatted_parts.append(token)
        is_last = (idx == len(timeline) - 1)
        if not is_last:
            fmt_instructions.append({"start": cursor, "end": cursor + len(token), "strikethrough": True})
        cursor += len(token)
        if not is_last:
            cursor += 1  # account for the space
    return " ".join(formatted_parts), fmt_instructions

def format_due_date_with_history(current_date: str, date_history: List[Dict]) -> Tuple[str, List[Dict]]:
    """EPICS: show last 4 dates (previous 3 struck, current clean)."""
    history_iso = _extract_history_strings(date_history)
    return _format_tape(current_date, history_iso, max_visible=4)

def format_due_date_with_history_deliverable(current_date: str, date_history: List[Dict]) -> Tuple[str, List[Dict]]:
    """DELIVERABLES: show last 2 dates (previous struck, current clean)."""
    history_iso = _extract_history_strings(date_history)
    return _format_tape(current_date, history_iso, max_visible=2)
