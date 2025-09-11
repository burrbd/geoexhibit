"""Time provider implementations for GeoExhibit."""

import re
from datetime import datetime, timezone
from typing import Dict, Any, Iterable, Optional, List, Union
from .interfaces import TimeProvider, TimeSpan


class ConstantTimeProvider(TimeProvider):
    """
    Demo time provider that returns a constant time for all features.
    Useful for single-time analyses or testing.
    """
    
    def __init__(self, dt: datetime):
        """
        Initialize with a constant datetime.
        
        Args:
            dt: The datetime to use for all features
        """
        if dt.tzinfo is None:
            # Assume UTC if no timezone provided
            dt = dt.replace(tzinfo=timezone.utc)
        self.datetime = dt
    
    def for_feature(self, feature: Dict[str, Any]) -> Iterable[TimeSpan]:
        """Return a single TimeSpan with the constant datetime."""
        return [TimeSpan(start=self.datetime)]


class PropertyTimeProvider(TimeProvider):
    """
    Time provider that extracts time from feature properties.
    Supports both instant times and time ranges.
    """
    
    def __init__(self, 
                 start_property: str, 
                 end_property: Optional[str] = None,
                 date_format: str = "%Y-%m-%d",
                 timezone_info: Optional[timezone] = None):
        """
        Initialize property-based time provider.
        
        Args:
            start_property: Name of property containing start time
            end_property: Optional name of property containing end time
            date_format: strptime format for parsing dates
            timezone_info: Timezone for parsed dates (defaults to UTC)
        """
        self.start_property = start_property
        self.end_property = end_property
        self.date_format = date_format
        self.timezone_info = timezone_info or timezone.utc
    
    def for_feature(self, feature: Dict[str, Any]) -> Iterable[TimeSpan]:
        """Extract time spans from feature properties."""
        props = feature.get("properties", {})
        
        if self.start_property not in props:
            raise ValueError(f"Feature missing required time property: {self.start_property}")
        
        start_str = props[self.start_property]
        if isinstance(start_str, str):
            start_dt = datetime.strptime(start_str, self.date_format)
            start_dt = start_dt.replace(tzinfo=self.timezone_info)
        elif isinstance(start_str, datetime):
            start_dt = start_str
            if start_dt.tzinfo is None:
                start_dt = start_dt.replace(tzinfo=self.timezone_info)
        else:
            raise ValueError(f"Invalid start time format: {start_str}")
        
        end_dt = None
        if self.end_property and self.end_property in props:
            end_str = props[self.end_property]
            if isinstance(end_str, str):
                end_dt = datetime.strptime(end_str, self.date_format)
                end_dt = end_dt.replace(tzinfo=self.timezone_info)
            elif isinstance(end_str, datetime):
                end_dt = end_str
                if end_dt.tzinfo is None:
                    end_dt = end_dt.replace(tzinfo=self.timezone_info)
        
        return [TimeSpan(start=start_dt, end=end_dt)]


class ListTimeProvider(TimeProvider):
    """
    Time provider that provides a predefined list of times for all features.
    Useful for time series analysis where the same times apply to all features.
    """
    
    def __init__(self, time_spans: List[TimeSpan]):
        """
        Initialize with a list of time spans.
        
        Args:
            time_spans: List of TimeSpan objects to use for all features
        """
        if not time_spans:
            raise ValueError("time_spans cannot be empty")
        self.time_spans = time_spans
    
    def for_feature(self, feature: Dict[str, Any]) -> Iterable[TimeSpan]:
        """Return the predefined list of time spans."""
        return self.time_spans


class YearRangeTimeProvider(TimeProvider):
    """
    Time provider that generates a range of years for each feature.
    Useful for multi-year analyses.
    """
    
    def __init__(self, start_year: int, end_year: int, month: int = 1, day: int = 1):
        """
        Initialize with year range parameters.
        
        Args:
            start_year: First year (inclusive)
            end_year: Last year (inclusive)  
            month: Month to use for all years (default: January)
            day: Day to use for all years (default: 1st)
        """
        self.start_year = start_year
        self.end_year = end_year
        self.month = month
        self.day = day
        
        if start_year > end_year:
            raise ValueError("start_year must be <= end_year")
    
    def for_feature(self, feature: Dict[str, Any]) -> Iterable[TimeSpan]:
        """Generate time spans for each year in the range."""
        time_spans = []
        for year in range(self.start_year, self.end_year + 1):
            dt = datetime(year, self.month, self.day, tzinfo=timezone.utc)
            time_spans.append(TimeSpan(start=dt))
        return time_spans


def create_time_provider(provider_spec: str) -> TimeProvider:
    """
    Create a time provider from a specification string.
    
    Format: "module:callable" or built-in provider names.
    
    Built-in providers:
    - "constant:YYYY-MM-DD" - ConstantTimeProvider with specified date
    - "constant:YYYY-MM-DDTHH:MM:SSZ" - ConstantTimeProvider with specified datetime
    - "years:START-END" - YearRangeTimeProvider from START to END year
    
    Args:
        provider_spec: Provider specification string
        
    Returns:
        Configured TimeProvider instance
    """
    if provider_spec.startswith("constant:"):
        date_str = provider_spec[9:]  # Remove "constant:" prefix
        try:
            if 'T' in date_str:
                # Full datetime format
                dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            else:
                # Date only format
                dt = datetime.strptime(date_str, "%Y-%m-%d")
                dt = dt.replace(tzinfo=timezone.utc)
            return ConstantTimeProvider(dt)
        except ValueError as e:
            raise ValueError(f"Invalid constant time format '{date_str}': {e}")
    
    elif provider_spec.startswith("years:"):
        range_str = provider_spec[6:]  # Remove "years:" prefix
        try:
            start_year, end_year = map(int, range_str.split('-'))
            return YearRangeTimeProvider(start_year, end_year)
        except ValueError as e:
            raise ValueError(f"Invalid year range format '{range_str}': {e}")
    
    elif ":" in provider_spec:
        # Module:callable format
        try:
            module_path, callable_name = provider_spec.rsplit(":", 1)
            # Import the module and get the callable
            import importlib
            module = importlib.import_module(module_path)
            provider_callable = getattr(module, callable_name)
            
            if not callable(provider_callable):
                raise ValueError(f"{callable_name} is not callable")
                
            # Try to call it - assumes no arguments for now
            return provider_callable()
            
        except (ImportError, AttributeError) as e:
            raise ValueError(f"Could not import time provider '{provider_spec}': {e}")
    
    else:
        raise ValueError(f"Invalid time provider specification: {provider_spec}")


def validate_time_spans(time_spans: List[TimeSpan]) -> None:
    """
    Validate a list of time spans.
    
    Args:
        time_spans: List of TimeSpan objects to validate
        
    Raises:
        ValueError: If any time span is invalid
    """
    if not time_spans:
        raise ValueError("time_spans cannot be empty")
    
    for i, span in enumerate(time_spans):
        if not isinstance(span, TimeSpan):
            raise ValueError(f"time_spans[{i}] is not a TimeSpan instance")
        
        if span.end is not None and span.start >= span.end:
            raise ValueError(f"time_spans[{i}]: start time must be before end time")
        
        if span.start.tzinfo is None:
            raise ValueError(f"time_spans[{i}]: start time must have timezone info")
        
        if span.end is not None and span.end.tzinfo is None:
            raise ValueError(f"time_spans[{i}]: end time must have timezone info")


class DeclarativeTimeProvider(TimeProvider):
    """
    Declarative time provider that extracts time information based on configuration.
    Supports multiple extractors: attribute_date, attribute_interval, etc.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize declarative time provider with configuration.
        
        Args:
            config: Time configuration dict from GeoExhibitConfig
        """
        self.config = config
        self.extractor = config["extractor"]
        self.field = config.get("field", "")
        self.format_str = config.get("format", "auto")
        self.timezone_str = config.get("tz", "UTC")
        self.timezone_info = timezone.utc if self.timezone_str == "UTC" else timezone.utc  # TODO: support other timezones
        
        # Validator configuration
        if self.extractor not in ["attribute_date", "attribute_interval", "fixed_annual_dates", "from_epoch", "regex_from_string"]:
            raise ValueError(f"Unknown extractor: {self.extractor}")
    
    def for_feature(self, feature: Dict[str, Any]) -> Iterable[TimeSpan]:
        """Extract time spans from feature based on extractor configuration."""
        if self.extractor == "attribute_date":
            return self._extract_attribute_date(feature)
        elif self.extractor == "attribute_interval":
            return self._extract_attribute_interval(feature)
        elif self.extractor == "fixed_annual_dates":
            return self._extract_fixed_annual_dates(feature)
        elif self.extractor == "from_epoch":
            return self._extract_from_epoch(feature)
        elif self.extractor == "regex_from_string":
            return self._extract_regex_from_string(feature)
        else:
            raise ValueError(f"Unsupported extractor: {self.extractor}")
    
    def _extract_attribute_date(self, feature: Dict[str, Any]) -> List[TimeSpan]:
        """Extract a single date from a feature attribute."""
        value = self._get_nested_value(feature, self.field)
        
        if value is None:
            return []
        
        # Handle list of dates if fanout is configured
        fanout_config = self.config.get("fanout", {})
        if fanout_config.get("as_list", False) and isinstance(value, list):
            time_spans = []
            for date_value in value:
                dt = self._parse_datetime(date_value)
                if dt:
                    time_spans.append(TimeSpan(start=dt))
            return time_spans
        else:
            dt = self._parse_datetime(value)
            return [TimeSpan(start=dt)] if dt else []
    
    def _extract_attribute_interval(self, feature: Dict[str, Any]) -> List[TimeSpan]:
        """Extract a date interval from feature attributes."""
        start_value = self._get_nested_value(feature, self.field)
        
        if start_value is None:
            return []
        
        start_dt = self._parse_datetime(start_value)
        if not start_dt:
            return []
        
        # Check for end field
        interval_config = self.config.get("interval", {})
        end_field = interval_config.get("end_field")
        end_dt = None
        
        if end_field:
            end_value = self._get_nested_value(feature, end_field)
            if end_value:
                end_dt = self._parse_datetime(end_value)
        
        # Use default duration if no end date
        if not end_dt:
            default_days = interval_config.get("default_days", 0)
            if default_days > 0:
                from datetime import timedelta
                end_dt = start_dt + timedelta(days=default_days)
        
        return [TimeSpan(start=start_dt, end=end_dt)]
    
    def _extract_fixed_annual_dates(self, feature: Dict[str, Any]) -> List[TimeSpan]:
        """Extract fixed annual dates (e.g., same day each year for a range)."""
        # This would be configured with year range and fixed date
        # For now, return empty - would need more config structure
        return []
    
    def _extract_from_epoch(self, feature: Dict[str, Any]) -> List[TimeSpan]:
        """Extract datetime from epoch timestamp."""
        value = self._get_nested_value(feature, self.field)
        
        if value is None:
            return []
        
        try:
            if isinstance(value, (int, float)):
                timestamp = value
            else:
                timestamp = float(value)
            
            # Assume milliseconds if > year 2100 in seconds (rough heuristic)
            if timestamp > 4102444800:  # Jan 1, 2100 in seconds
                timestamp = timestamp / 1000  # Convert from milliseconds
            
            dt = datetime.fromtimestamp(timestamp, tz=self.timezone_info)
            return [TimeSpan(start=dt)]
            
        except (ValueError, TypeError):
            return []
    
    def _extract_regex_from_string(self, feature: Dict[str, Any]) -> List[TimeSpan]:
        """Extract date from string using regex pattern."""
        value = self._get_nested_value(feature, self.field)
        
        if not isinstance(value, str):
            return []
        
        # Default pattern for ISO-like dates in strings
        regex_config = self.config.get("regex", {})
        pattern = regex_config.get("pattern", r"\d{4}-\d{2}-\d{2}")
        
        matches = re.findall(pattern, value)
        if matches:
            dt = self._parse_datetime(matches[0])
            return [TimeSpan(start=dt)] if dt else []
        
        return []
    
    def _get_nested_value(self, data: Dict[str, Any], field_path: str) -> Any:
        """Get value from nested dictionary using dot notation."""
        keys = field_path.split('.')
        current = data
        
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        
        return current
    
    def _parse_datetime(self, value: Any) -> Optional[datetime]:
        """Parse datetime from various formats."""
        if isinstance(value, datetime):
            return value.replace(tzinfo=self.timezone_info) if value.tzinfo is None else value
        
        if not isinstance(value, str):
            return None
        
        # Auto-format detection
        if self.format_str == "auto":
            # Try common formats
            formats = [
                "%Y-%m-%d",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%d %H:%M:%S",
                "%m/%d/%Y",
                "%d/%m/%Y",
                "%Y%m%d"
            ]
            
            for fmt in formats:
                try:
                    dt = datetime.strptime(value, fmt)
                    return dt.replace(tzinfo=self.timezone_info)
                except ValueError:
                    continue
            
            # Try ISO format parsing
            try:
                if value.endswith('Z'):
                    value = value[:-1] + '+00:00'
                dt = datetime.fromisoformat(value)
                return dt.replace(tzinfo=self.timezone_info) if dt.tzinfo is None else dt
            except ValueError:
                pass
            
            return None
        else:
            # Use specified format
            try:
                dt = datetime.strptime(value, self.format_str)
                return dt.replace(tzinfo=self.timezone_info)
            except ValueError:
                return None


def create_declarative_time_provider(config: Dict[str, Any]) -> DeclarativeTimeProvider:
    """
    Create a declarative time provider from configuration.
    
    Args:
        config: Time configuration dict
        
    Returns:
        Configured DeclarativeTimeProvider
    """
    return DeclarativeTimeProvider(config)