"""Tests for TimeProvider interface and implementations."""

from datetime import datetime, timezone

from geoexhibit.time_provider import (
    ConstantTimeProvider,
    create_time_provider,
)


def test_constant_time_provider():
    """Test ConstantTimeProvider returns the same time for all features."""
    dt = datetime(2023, 9, 15, 12, 0, 0, tzinfo=timezone.utc)
    provider = ConstantTimeProvider(dt)

    feature1 = {"type": "Feature", "properties": {"id": "1"}}
    feature2 = {"type": "Feature", "properties": {"id": "2"}}

    spans1 = list(provider.for_feature(feature1))
    spans2 = list(provider.for_feature(feature2))

    assert len(spans1) == 1
    assert len(spans2) == 1
    assert spans1[0].start == dt
    assert spans2[0].start == dt
    assert spans1[0].is_instant is True
    assert spans2[0].is_instant is True


def test_constant_time_provider_with_naive_datetime():
    """Test ConstantTimeProvider adds UTC timezone to naive datetime."""
    naive_dt = datetime(2023, 9, 15, 12, 0, 0)
    provider = ConstantTimeProvider(naive_dt)

    feature = {"type": "Feature", "properties": {}}
    spans = list(provider.for_feature(feature))

    assert len(spans) == 1
    assert spans[0].start.tzinfo == timezone.utc


def test_create_time_provider_constant_date():
    """Test creating ConstantTimeProvider from date string."""
    provider = create_time_provider("constant:2023-09-15")

    assert isinstance(provider, ConstantTimeProvider)

    feature = {"type": "Feature", "properties": {}}
    spans = list(provider.for_feature(feature))

    assert len(spans) == 1
    assert spans[0].start.year == 2023
    assert spans[0].start.month == 9
    assert spans[0].start.day == 15
    assert spans[0].start.tzinfo == timezone.utc


def test_create_time_provider_constant_datetime():
    """Test creating ConstantTimeProvider from datetime string."""
    provider = create_time_provider("constant:2023-09-15T14:30:00Z")

    assert isinstance(provider, ConstantTimeProvider)

    feature = {"type": "Feature", "properties": {}}
    spans = list(provider.for_feature(feature))

    assert len(spans) == 1
    assert spans[0].start.hour == 14
    assert spans[0].start.minute == 30


def test_create_time_provider_invalid_spec():
    """Test error handling for invalid provider specs."""
    try:
        create_time_provider("invalid-spec")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Invalid time provider specification" in str(e)


def test_create_time_provider_invalid_constant():
    """Test error handling for invalid constant time format."""
    try:
        create_time_provider("constant:invalid-date")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Invalid constant time format" in str(e)


def test_create_time_provider_missing_module():
    """Test error handling for missing callable module."""
    try:
        create_time_provider("nonexistent.module:some_function")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Could not import time provider" in str(e)
