"""Declarative time provider implementation for GeoExhibit."""

import re
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from .time_provider import TimeProvider
from .timespan import TimeSpan


class DeclarativeTimeProvider(TimeProvider):
    """
    Declarative time provider that extracts time information based on configuration.
    Supports multiple extractors: attribute_date, attribute_interval, etc.
    """

    def __init__(self, config: Dict[str, Any]):
        """Initialize declarative time provider with configuration."""
        self.config = config
        self.extractor = config["extractor"]
        self.field = config.get("field", "")
        self.format_str = config.get("format", "auto")
        self.timezone_str = config.get("tz", "UTC")
        self.timezone_info = timezone.utc

    def for_feature(self, feature: Dict[str, Any]) -> List[TimeSpan]:
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

        interval_config = self.config.get("interval", {})
        end_field = interval_config.get("end_field")
        end_dt = None

        if end_field:
            end_value = self._get_nested_value(feature, end_field)
            if end_value:
                end_dt = self._parse_datetime(end_value)

        if not end_dt:
            default_days = interval_config.get("default_days", 0)
            if default_days > 0:
                from datetime import timedelta

                end_dt = start_dt + timedelta(days=default_days)

        return [TimeSpan(start=start_dt, end=end_dt)]

    def _extract_fixed_annual_dates(self, feature: Dict[str, Any]) -> List[TimeSpan]:
        """Extract fixed annual dates (e.g., same day each year for a range)."""
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

        regex_config = self.config.get("regex", {})
        pattern = regex_config.get("pattern", r"\d{4}-\d{2}-\d{2}")

        matches = re.findall(pattern, value)
        if matches:
            dt = self._parse_datetime(matches[0])
            return [TimeSpan(start=dt)] if dt else []

        return []

    def _get_nested_value(self, data: Dict[str, Any], field_path: str) -> Any:
        """Get value from nested dictionary using dot notation."""
        keys = field_path.split(".")
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
            return (
                value.replace(tzinfo=self.timezone_info)
                if value.tzinfo is None
                else value
            )

        if not isinstance(value, str):
            return None

        if self.format_str == "auto":
            formats = [
                "%Y-%m-%d",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%d %H:%M:%S",
                "%m/%d/%Y",
                "%d/%m/%Y",
                "%Y%m%d",
            ]

            for fmt in formats:
                try:
                    dt = datetime.strptime(value, fmt)
                    return dt.replace(tzinfo=self.timezone_info)
                except ValueError:
                    continue

            try:
                if value.endswith("Z"):
                    value = value[:-1] + "+00:00"
                dt = datetime.fromisoformat(value)
                return (
                    dt.replace(tzinfo=self.timezone_info) if dt.tzinfo is None else dt
                )
            except ValueError:
                pass

            return None
        else:
            try:
                dt = datetime.strptime(value, self.format_str)
                return dt.replace(tzinfo=self.timezone_info)
            except ValueError:
                return None


def create_declarative_time_provider(config: Dict[str, Any]) -> DeclarativeTimeProvider:
    """Create a declarative time provider from configuration."""
    return DeclarativeTimeProvider(config)
