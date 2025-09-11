"""Tests for DeclarativeTimeProvider implementation."""

from geoexhibit.declarative_time import (
    DeclarativeTimeProvider,
    create_declarative_time_provider,
)


def test_attribute_date_extractor():
    """Test extracting single date from feature attribute."""
    config = {
        "extractor": "attribute_date",
        "field": "properties.fire_date",
        "format": "auto",
        "tz": "UTC",
    }
    provider = DeclarativeTimeProvider(config)

    feature = {
        "properties": {"fire_date": "2023-09-15"},
        "geometry": {"type": "Point", "coordinates": [0, 0]},
    }

    spans = list(provider.for_feature(feature))
    assert len(spans) == 1
    assert spans[0].start.year == 2023
    assert spans[0].start.month == 9
    assert spans[0].start.day == 15
    assert spans[0].is_instant


def test_attribute_date_missing_field():
    """Test attribute_date extractor with missing field."""
    config = {
        "extractor": "attribute_date",
        "field": "properties.missing_date",
        "format": "auto",
        "tz": "UTC",
    }
    provider = DeclarativeTimeProvider(config)

    feature = {"properties": {"other_field": "value"}}

    spans = list(provider.for_feature(feature))
    assert len(spans) == 0


def test_attribute_date_list_fanout():
    """Test attribute_date extractor with list fanout."""
    config = {
        "extractor": "attribute_date",
        "field": "properties.analysis_dates",
        "format": "auto",
        "tz": "UTC",
        "fanout": {"as_list": True},
    }
    provider = DeclarativeTimeProvider(config)

    feature = {
        "properties": {"analysis_dates": ["2023-01-01", "2023-06-01", "2023-12-01"]}
    }

    spans = list(provider.for_feature(feature))
    assert len(spans) == 3
    assert spans[0].start.month == 1
    assert spans[1].start.month == 6
    assert spans[2].start.month == 12


def test_attribute_interval_extractor():
    """Test extracting date interval from feature attributes."""
    config = {
        "extractor": "attribute_interval",
        "field": "properties.start_date",
        "format": "auto",
        "tz": "UTC",
        "interval": {"end_field": "properties.end_date"},
    }
    provider = DeclarativeTimeProvider(config)

    feature = {
        "properties": {
            "start_date": "2023-09-15",
            "end_date": "2023-09-20",
        }
    }

    spans = list(provider.for_feature(feature))
    assert len(spans) == 1
    assert spans[0].start.day == 15
    assert spans[0].end.day == 20
    assert not spans[0].is_instant


def test_attribute_interval_with_default_duration():
    """Test interval extractor with default duration fallback."""
    config = {
        "extractor": "attribute_interval",
        "field": "properties.start_date",
        "format": "auto",
        "tz": "UTC",
        "interval": {"default_days": 7},
    }
    provider = DeclarativeTimeProvider(config)

    feature = {"properties": {"start_date": "2023-09-15"}}

    spans = list(provider.for_feature(feature))
    assert len(spans) == 1
    assert spans[0].start.day == 15
    assert spans[0].end.day == 22  # 7 days later
    assert not spans[0].is_instant


def test_from_epoch_extractor():
    """Test extracting datetime from epoch timestamp."""
    config = {
        "extractor": "from_epoch",
        "field": "properties.timestamp",
        "tz": "UTC",
    }
    provider = DeclarativeTimeProvider(config)

    # Test seconds timestamp
    feature = {"properties": {"timestamp": 1694779200}}  # 2023-09-15 12:00:00 UTC

    spans = list(provider.for_feature(feature))
    assert len(spans) == 1
    assert spans[0].start.year == 2023
    assert spans[0].start.month == 9
    assert spans[0].start.day == 15
    assert spans[0].start.hour == 12


def test_from_epoch_milliseconds():
    """Test epoch extractor with milliseconds timestamp."""
    config = {
        "extractor": "from_epoch",
        "field": "properties.timestamp_ms",
        "tz": "UTC",
    }
    provider = DeclarativeTimeProvider(config)

    feature = {"properties": {"timestamp_ms": 1694779200000}}  # milliseconds

    spans = list(provider.for_feature(feature))
    assert len(spans) == 1
    assert spans[0].start.year == 2023
    assert spans[0].start.month == 9
    assert spans[0].start.day == 15
    assert spans[0].start.hour == 12


def test_regex_from_string_extractor():
    """Test extracting date from string using regex."""
    config = {
        "extractor": "regex_from_string",
        "field": "properties.description",
        "format": "auto",
        "tz": "UTC",
        "regex": {"pattern": r"\d{4}-\d{2}-\d{2}"},
    }
    provider = DeclarativeTimeProvider(config)

    feature = {
        "properties": {"description": "Fire occurred on 2023-09-15 and spread quickly"}
    }

    spans = list(provider.for_feature(feature))
    assert len(spans) == 1
    assert spans[0].start.year == 2023
    assert spans[0].start.month == 9
    assert spans[0].start.day == 15


def test_regex_from_string_no_match():
    """Test regex extractor with no matching pattern."""
    config = {
        "extractor": "regex_from_string",
        "field": "properties.description",
        "regex": {"pattern": r"\d{4}-\d{2}-\d{2}"},
    }
    provider = DeclarativeTimeProvider(config)

    feature = {"properties": {"description": "No dates in this text"}}

    spans = list(provider.for_feature(feature))
    assert len(spans) == 0


def test_nested_field_access():
    """Test accessing nested fields with dot notation."""
    config = {
        "extractor": "attribute_date",
        "field": "properties.metadata.analysis_date",
        "format": "auto",
    }
    provider = DeclarativeTimeProvider(config)

    feature = {
        "properties": {
            "metadata": {"analysis_date": "2023-09-15"},
            "other": "data",
        }
    }

    spans = list(provider.for_feature(feature))
    assert len(spans) == 1
    assert spans[0].start.day == 15


def test_parse_datetime_various_formats():
    """Test datetime parsing with various format strings."""
    config = {
        "extractor": "attribute_date",
        "field": "properties.date",
        "format": "auto",
    }
    provider = DeclarativeTimeProvider(config)

    test_cases = [
        ("2023-09-15", (2023, 9, 15)),
        ("2023-09-15T14:30:00", (2023, 9, 15, 14, 30)),
        ("2023-09-15T14:30:00Z", (2023, 9, 15, 14, 30)),
        ("2023-09-15 14:30:00", (2023, 9, 15, 14, 30)),
        ("09/15/2023", (2023, 9, 15)),
        ("20230915", (2023, 9, 15)),
    ]

    for date_str, expected_parts in test_cases:
        result = provider._parse_datetime(date_str)
        assert result is not None, f"Failed to parse: {date_str}"
        assert result.year == expected_parts[0]
        assert result.month == expected_parts[1]
        assert result.day == expected_parts[2]

        if len(expected_parts) >= 4:
            assert result.hour == expected_parts[3]
        if len(expected_parts) >= 5:
            assert result.minute == expected_parts[4]


def test_parse_datetime_custom_format():
    """Test datetime parsing with custom format specification."""
    config = {
        "extractor": "attribute_date",
        "field": "properties.date",
        "format": "%d/%m/%Y",
    }
    provider = DeclarativeTimeProvider(config)

    result = provider._parse_datetime("15/09/2023")
    assert result is not None
    assert result.year == 2023
    assert result.month == 9
    assert result.day == 15


def test_create_declarative_time_provider_function():
    """Test the factory function for creating declarative providers."""
    config = {
        "extractor": "attribute_date",
        "field": "properties.date",
        "format": "auto",
    }

    provider = create_declarative_time_provider(config)
    assert isinstance(provider, DeclarativeTimeProvider)
    assert provider.extractor == "attribute_date"
    assert provider.field == "properties.date"
