"""Data models for the Jira Due Date Analysis tool."""

from datetime import datetime, timezone
from enum import Enum, auto
from typing import List, Optional, Tuple, Dict
from dataclasses import dataclass, field

def ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Ensure a datetime is UTC timezone-aware."""
    if dt is None:
        return None
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt

class StartDateScenario(Enum):
    """Available scenarios for determining the start date."""
    DELIVERABLE_START_DATE = "given_start_date"
    EARLIEST_EPIC_START = "earliest_epic_start"
    FIRST_ISSUE_IN_PROGRESS = "first_issue_in_progress"

@dataclass
class DateShift:
    """Represents a series of date shifts for an issue."""
    issue_key: str
    issue_type: str
    issue_summary: str    
    start_date: datetime
    end_date: datetime
    initial_due_date: datetime
    # Store tuples of (change_date, shift_date) instead of just shift dates
    date_changes: List[Tuple[datetime, datetime]] = field(default_factory=list)
    _total_delay: Optional[int] = field(default=None, init=False, repr=False)
    
    def __post_init__(self):
        """Ensure all dates are timezone-aware."""
        self.start_date = ensure_utc(self.start_date)
        self.end_date = ensure_utc(self.end_date)
        self.initial_due_date = ensure_utc(self.initial_due_date)
        
        # Ensure all dates in the tuples are timezone-aware
        self.date_changes = [(ensure_utc(change_date), ensure_utc(shift_date)) 
                            for change_date, shift_date in self.date_changes]
    
    @property
    def shifts(self) -> List[datetime]:
        """Return just the shift dates for backward compatibility."""
        return [shift_date for _, shift_date in self.date_changes]

    @shifts.setter
    def shifts(self, values: List[datetime]):
        """Set shifts from a list of dates (for backward compatibility)."""
        # Create dummy change dates equal to the shift dates
        self.date_changes = [(date, date) for date in values]
    
    @property
    def total_shifts(self) -> int:
        """Return the total number of due date shifts."""
        return len(self.date_changes)
    
    @property
    def total_delay(self) -> int:
        """Return the total number of days between initial_due_date and end_date."""
        if self._total_delay is None:
            if self.end_date is None or self.initial_due_date is None:
                return None
            
            self._total_delay = (self.end_date - self.initial_due_date).days
        return self._total_delay

@dataclass
class StartDates:
    """Contains various start dates for a deliverable."""
    deliverable_key: str
    deliverable_start: Optional[datetime] = None
    skip_deliverable: Optional[bool] = False
    deliverable_in_progress: Optional[datetime] = None
    earliest_epic_start: Optional[datetime] = None
    earliest_epic_in_progress: Optional[datetime] = None
    earliest_issue_in_progress: Optional[datetime] = None
    earliest_epic_key: Optional[str] = None
    earliest_epic_in_progress_key: Optional[str] = None
    earliest_issue_key: Optional[str] = None
    
    def __post_init__(self):
        """Ensure all dates are timezone-aware."""
        for field_name, value in self.__dict__.items():
            if isinstance(value, datetime):
                setattr(self, field_name, ensure_utc(value))
    
    def get_start_date(self, scenario: StartDateScenario) -> Optional[datetime]:
        """Get the appropriate start date based on the scenario."""
        return {
            StartDateScenario.DELIVERABLE_START_DATE: self.deliverable_start,
            StartDateScenario.EARLIEST_EPIC_START: self.earliest_epic_start,
            StartDateScenario.FIRST_ISSUE_IN_PROGRESS: self.earliest_issue_in_progress
        }.get(scenario)

@dataclass
class AnalysisResult:
    """Contains the results of a due date shift analysis."""
    team: str
    project: str
    scenario: StartDateScenario
    period_start: datetime
    period_end: datetime
    date_shifts: List[DateShift]
    start_dates: List[StartDates] = field(default_factory=list)
    show_start_dates: bool = False
    
    # Cached calculations
    _average_shifts: Optional[float] = field(default=None, init=False, repr=False)
    _average_delay: Optional[float] = field(default=None, init=False, repr=False)
    
    def __post_init__(self):
        """Ensure all dates are timezone-aware."""
        self.period_start = ensure_utc(self.period_start)
        self.period_end = ensure_utc(self.period_end)
    
    @property
    def average_shifts(self) -> float:
        """Calculate the average number of shifts."""
        if self._average_shifts is None:
            self._average_shifts = (
                sum(shift.total_shifts for shift in self.date_shifts) / len(self.date_shifts)
                if self.date_shifts else 0.0
            )
        return self._average_shifts
    
    @property
    def average_delay(self) -> float:
        """Calculate the average delay in days."""
        if self._average_delay is None:
            self._average_delay = (
                sum(shift.total_delay for shift in self.date_shifts) / len(self.date_shifts)
                if self.date_shifts else 0.0
            )
        return self._average_delay