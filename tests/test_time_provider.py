"""Tests for TimeProvider interface and implementations."""

from datetime import datetime, timezone

from geoexhibit.time_provider import (
    TimeProvider,
    ConstantTimeProvider,
    create_time_provider,
)


def test_time_provider_abstract():
    """Test that TimeProvider cannot be instantiated directly."""
    try:
        TimeProvider()
        assert False, "Should have raised TypeError for abstract class"
    except TypeError:
        pass  # Expected - abstract class cannot be instantiated


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


def test_create_time_provider_not_callable():
    """Test error handling when module attribute is not callable."""
    try:
        # Try to use a non-callable attribute
        create_time_provider("os:name")  # os.name is a string, not callable
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "is not callable" in str(e)


def test_create_time_provider_wrong_return_type():
    """Test error handling when callable returns wrong type."""

    # Create a temporary module for testing
    import tempfile
    import os
    import sys

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(
            """
def bad_provider():
    return "not a time provider"
"""
        )
        temp_module_path = f.name

    try:
        # Add temp directory to Python path
        temp_dir = os.path.dirname(temp_module_path)
        temp_module_name = os.path.basename(temp_module_path)[:-3]  # Remove .py

        if temp_dir not in sys.path:
            sys.path.insert(0, temp_dir)

        try:
            create_time_provider(f"{temp_module_name}:bad_provider")
            assert False, "Should have raised ValueError for wrong return type"
        except ValueError as e:
            assert "must return a TimeProvider instance" in str(e)

    finally:
        # Cleanup
        if temp_dir in sys.path:
            sys.path.remove(temp_dir)
        os.unlink(temp_module_path)


def test_create_time_provider_missing_attribute():
    """Test error handling when module doesn't have the specified attribute."""
    try:
        create_time_provider("datetime:nonexistent_function")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Could not import time provider" in str(e)
