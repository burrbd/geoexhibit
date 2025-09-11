"""Example callable time providers for GeoExhibit."""

from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Iterable

from geoexhibit.core.interfaces import TimeSpan


def monthly_series_2023(feature: Dict[str, Any]) -> Iterable[TimeSpan]:
    """
    Example time provider that generates monthly time spans for 2023.
    
    Args:
        feature: GeoJSON feature (unused in this example)
        
    Returns:
        Iterable of TimeSpan objects for each month in 2023
    """
    time_spans = []
    
    for month in range(1, 13):  # January to December
        start_date = datetime(2023, month, 1, tzinfo=timezone.utc)
        
        # Calculate end of month
        if month == 12:
            end_date = datetime(2023 + 1, 1, 1, tzinfo=timezone.utc) - timedelta(days=1)
        else:
            end_date = datetime(2023, month + 1, 1, tzinfo=timezone.utc) - timedelta(days=1)
        
        time_spans.append(TimeSpan(start=start_date, end=end_date))
    
    return time_spans


def fire_season_windows(feature: Dict[str, Any]) -> Iterable[TimeSpan]:
    """
    Example time provider that generates time spans for fire season windows.
    
    Uses feature properties to determine which seasons to include.
    
    Args:
        feature: GeoJSON feature with fire season information
        
    Returns:
        Iterable of TimeSpan objects for relevant fire seasons
    """
    props = feature.get("properties", {})
    
    # Look for year range in properties
    start_year = props.get("analysis_start_year", 2020)
    end_year = props.get("analysis_end_year", 2023)
    
    time_spans = []
    
    for year in range(start_year, end_year + 1):
        # Australian fire season: October to March
        # Split into early season (Oct-Dec) and late season (Jan-Mar)
        
        # Early season: October 1 to December 31
        early_start = datetime(year, 10, 1, tzinfo=timezone.utc)
        early_end = datetime(year, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
        time_spans.append(TimeSpan(start=early_start, end=early_end))
        
        # Late season: January 1 to March 31 (next year)
        late_start = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
        late_end = datetime(year + 1, 3, 31, 23, 59, 59, tzinfo=timezone.utc)
        time_spans.append(TimeSpan(start=late_start, end=late_end))
    
    return time_spans


def event_driven_analysis(feature: Dict[str, Any]) -> Iterable[TimeSpan]:
    """
    Example time provider that creates analysis windows around specific events.
    
    Args:
        feature: GeoJSON feature with event information
        
    Returns:
        Iterable of TimeSpan objects around event dates
    """
    props = feature.get("properties", {})
    
    # Look for event date in properties
    event_date_str = props.get("event_date")
    if not event_date_str:
        return []
    
    try:
        # Parse event date
        event_date = datetime.fromisoformat(event_date_str.replace('Z', '+00:00'))
        if event_date.tzinfo is None:
            event_date = event_date.replace(tzinfo=timezone.utc)
    except (ValueError, AttributeError):
        return []
    
    time_spans = []
    
    # Pre-event window (30 days before)
    pre_start = event_date - timedelta(days=30)
    pre_end = event_date - timedelta(days=1)
    time_spans.append(TimeSpan(start=pre_start, end=pre_end))
    
    # Event window (event day)
    time_spans.append(TimeSpan(start=event_date))
    
    # Post-event windows
    post_intervals = [7, 30, 90]  # 7 days, 30 days, 90 days after
    
    for days_after in post_intervals:
        post_date = event_date + timedelta(days=days_after)
        time_spans.append(TimeSpan(start=post_date))
    
    return time_spans


def quarterly_analysis(feature: Dict[str, Any]) -> Iterable[TimeSpan]:
    """
    Example time provider that generates quarterly time spans.
    
    Args:
        feature: GeoJSON feature
        
    Returns:
        Iterable of TimeSpan objects for quarters
    """
    props = feature.get("properties", {})
    year = props.get("analysis_year", 2023)
    
    quarters = [
        (1, 1, 3, 31),    # Q1: Jan-Mar
        (4, 1, 6, 30),    # Q2: Apr-Jun  
        (7, 1, 9, 30),    # Q3: Jul-Sep
        (10, 1, 12, 31)   # Q4: Oct-Dec
    ]
    
    time_spans = []
    
    for start_month, start_day, end_month, end_day in quarters:
        start_date = datetime(year, start_month, start_day, tzinfo=timezone.utc)
        end_date = datetime(year, end_month, end_day, 23, 59, 59, tzinfo=timezone.utc)
        time_spans.append(TimeSpan(start=start_date, end=end_date))
    
    return time_spans