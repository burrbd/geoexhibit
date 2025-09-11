"""Tests for TimeSpan model."""

from datetime import datetime, timezone

from geoexhibit.timespan import TimeSpan


def test_timespan_instant():
    """Test instant TimeSpan (no end time)."""
    dt = datetime(2023, 9, 15, 12, 0, 0, tzinfo=timezone.utc)
    span = TimeSpan(start=dt)
    
    assert span.is_instant is True
    assert span.to_stac_datetime() == dt


def test_timespan_interval():
    """Test interval TimeSpan (start and end)."""
    start_dt = datetime(2023, 9, 15, 12, 0, 0, tzinfo=timezone.utc)
    end_dt = datetime(2023, 9, 16, 12, 0, 0, tzinfo=timezone.utc)
    span = TimeSpan(start=start_dt, end=end_dt)
    
    assert span.is_instant is False
    expected = "2023-09-15T12:00:00+00:00Z/2023-09-16T12:00:00+00:00Z"
    assert span.to_stac_datetime() == expected