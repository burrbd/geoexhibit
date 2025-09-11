"""Time provider interface and implementations for GeoExhibit."""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Dict, Any, Iterable

from .timespan import TimeSpan


class TimeProvider(ABC):
    """Provider for extracting time information from features."""

    @abstractmethod
    def for_feature(self, feature: Dict[str, Any]) -> Iterable[TimeSpan]:
        """Extract time spans for the given feature."""
        pass


class ConstantTimeProvider(TimeProvider):
    """Demo time provider that returns a constant time for all features."""

    def __init__(self, dt: datetime):
        """Initialize with a constant datetime."""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        self.datetime = dt

    def for_feature(self, feature: Dict[str, Any]) -> Iterable[TimeSpan]:
        """Return a single TimeSpan with the constant datetime."""
        return [TimeSpan(start=self.datetime)]


def create_time_provider(provider_spec: str) -> TimeProvider:
    """
    Create a time provider from a specification string.

    Format: "module:callable" or built-in provider names.

    Built-in providers:
    - "constant:YYYY-MM-DD" - ConstantTimeProvider with specified date
    - "constant:YYYY-MM-DDTHH:MM:SSZ" - ConstantTimeProvider with specified datetime

    Args:
        provider_spec: Provider specification string

    Returns:
        Configured TimeProvider instance
    """
    if provider_spec.startswith("constant:"):
        date_str = provider_spec[9:]  # Remove "constant:" prefix
        try:
            if "T" in date_str:
                dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            else:
                dt = datetime.strptime(date_str, "%Y-%m-%d")
                dt = dt.replace(tzinfo=timezone.utc)
            return ConstantTimeProvider(dt)
        except ValueError as e:
            raise ValueError(f"Invalid constant time format '{date_str}': {e}")

    elif ":" in provider_spec:
        try:
            module_path, callable_name = provider_spec.rsplit(":", 1)
            import importlib

            module = importlib.import_module(module_path)
            provider_callable = getattr(module, callable_name)

            if not callable(provider_callable):
                raise ValueError(f"{callable_name} is not callable")

            result = provider_callable()
            if not isinstance(result, TimeProvider):
                raise ValueError(
                    f"{callable_name} must return a TimeProvider instance, "
                    f"got {type(result)}"
                )
            return result

        except (ImportError, AttributeError) as e:
            raise ValueError(f"Could not import time provider '{provider_spec}': {e}")

    else:
        raise ValueError(f"Invalid time provider specification: {provider_spec}")
