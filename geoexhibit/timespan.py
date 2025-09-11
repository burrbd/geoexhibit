"""Time span data model for GeoExhibit."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Union


@dataclass
class TimeSpan:
    """Represents a time span for analysis."""

    start: datetime
    end: Optional[datetime] = None

    @property
    def is_instant(self) -> bool:
        """True if this represents an instant in time."""
        return self.end is None

    def to_stac_datetime(self) -> Union[datetime, str]:
        """Convert to STAC-compatible datetime format."""
        if self.is_instant:
            return self.start
        assert self.end is not None  # For mypy - we know it's not None if not instant
        return f"{self.start.isoformat()}Z/{self.end.isoformat()}Z"
