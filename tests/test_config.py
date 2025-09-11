"""Tests for configuration management."""

import json
import tempfile
from pathlib import Path
from typing import Any, Dict

from geoexhibit.config import (
    GeoExhibitConfig,
    load_config,
    validate_config,
    create_default_config,
)


def test_load_config_from_file():
    """Test loading configuration from JSON file."""
    config_data = {
        "project": {
            "name": "test-project",
            "collection_id": "test_collection",
            "title": "Test Collection",
            "description": "Test description",
        },
        "aws": {"s3_bucket": "test-bucket", "region": "us-west-2"},
        "map": {
            "pmtiles": {
                "feature_id_property": "feature_id",
                "minzoom": 5,
                "maxzoom": 14,
            }
        },
        "stac": {"use_extensions": ["proj"], "geometry_in_item": True},
        "ids": {"strategy": "ulid", "prefix": "test"},
        "time": {
            "mode": "declarative",
            "extractor": "attribute_date",
            "field": "properties.date",
        },
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(config_data, f)
        temp_path = Path(f.name)

    try:
        config = load_config(temp_path)
        assert isinstance(config, GeoExhibitConfig)
        assert config.s3_bucket == "test-bucket"
        assert config.collection_id == "test_collection"
        assert config.project_name == "test-project"
    finally:
        temp_path.unlink()


def test_load_config_file_not_found():
    """Test error when configuration file doesn't exist."""
    try:
        load_config(Path("/nonexistent/config.json"))
        assert False, "Should have raised FileNotFoundError"
    except FileNotFoundError:
        pass


def test_validate_config_missing_sections():
    """Test validation fails with missing required sections."""
    incomplete_config = {"project": {"name": "test"}}

    try:
        validate_config(incomplete_config)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Missing required configuration section" in str(e)


def test_validate_project_section():
    """Test project section validation."""
    base_config = _create_minimal_valid_config()

    base_config["project"] = {"name": "test"}
    try:
        validate_config(base_config)
        assert False, "Should have raised ValueError for missing fields"
    except ValueError as e:
        assert "Missing required project field" in str(e)


def test_validate_aws_section():
    """Test AWS section validation."""
    base_config = _create_minimal_valid_config()

    base_config["aws"] = {"region": "us-west-2"}
    try:
        validate_config(base_config)
        assert False, "Should have raised ValueError for missing s3_bucket"
    except ValueError as e:
        assert "Missing required AWS field: s3_bucket" in str(e)


def test_validate_time_section_invalid_mode():
    """Test time section validation with invalid mode."""
    base_config = _create_minimal_valid_config()

    base_config["time"] = {"mode": "invalid"}
    try:
        validate_config(base_config)
        assert False, "Should have raised ValueError for invalid mode"
    except ValueError as e:
        assert "time.mode must be 'declarative' or 'callable'" in str(e)


def test_validate_declarative_time_missing_extractor():
    """Test declarative time validation missing extractor."""
    base_config = _create_minimal_valid_config()

    base_config["time"] = {"mode": "declarative"}
    try:
        validate_config(base_config)
        assert False, "Should have raised ValueError for missing extractor"
    except ValueError as e:
        assert "requires 'extractor' field" in str(e)


def test_validate_declarative_time_invalid_extractor():
    """Test declarative time validation with invalid extractor."""
    base_config = _create_minimal_valid_config()

    base_config["time"] = {"mode": "declarative", "extractor": "invalid_extractor"}
    try:
        validate_config(base_config)
        assert False, "Should have raised ValueError for invalid extractor"
    except ValueError as e:
        assert "Invalid extractor" in str(e)


def test_validate_declarative_time_missing_field():
    """Test declarative time validation missing field for extractors that need it."""
    base_config = _create_minimal_valid_config()

    base_config["time"] = {"mode": "declarative", "extractor": "attribute_date"}
    try:
        validate_config(base_config)
        assert False, "Should have raised ValueError for missing field"
    except ValueError as e:
        assert "requires 'field' specification" in str(e)


def test_validate_callable_time_missing_provider():
    """Test callable time validation missing provider."""
    base_config = _create_minimal_valid_config()

    base_config["time"] = {"mode": "callable"}
    try:
        validate_config(base_config)
        assert False, "Should have raised ValueError for missing provider"
    except ValueError as e:
        assert "requires 'provider' field" in str(e)


def test_config_defaults():
    """Test that default values are set correctly."""
    base_config = _create_minimal_valid_config()

    del base_config["stac"]["use_extensions"]
    del base_config["stac"]["geometry_in_item"]
    del base_config["ids"]["strategy"]
    del base_config["time"]["format"]

    config = validate_config(base_config)

    assert config.use_extensions == ["proj", "raster", "processing"]
    assert config.stac["geometry_in_item"] is True
    assert config.ids["strategy"] == "ulid"
    assert config.time_config["format"] == "auto"
    assert config.time_config["tz"] == "UTC"


def test_config_properties():
    """Test GeoExhibitConfig property accessors."""
    config = validate_config(_create_minimal_valid_config())

    assert config.s3_bucket == "test-bucket"
    assert config.aws_region == "us-west-2"
    assert config.collection_id == "test_collection"
    assert config.project_name == "test-project"
    assert isinstance(config.use_extensions, list)
    assert isinstance(config.time_config, dict)


def test_create_default_config():
    """Test default configuration template creation."""
    default = create_default_config()

    assert "project" in default
    assert "aws" in default
    assert "map" in default
    assert "stac" in default
    assert "ids" in default
    assert "time" in default

    config = validate_config(default.copy())
    assert isinstance(config, GeoExhibitConfig)


def _create_minimal_valid_config() -> Dict[str, Any]:
    """Create a minimal valid configuration for testing."""
    return {
        "project": {
            "name": "test-project",
            "collection_id": "test_collection",
            "title": "Test Collection",
            "description": "Test description",
        },
        "aws": {"s3_bucket": "test-bucket", "region": "us-west-2"},
        "map": {"pmtiles": {"feature_id_property": "feature_id"}},
        "stac": {"use_extensions": ["proj"], "geometry_in_item": True},
        "ids": {"strategy": "ulid"},
        "time": {
            "mode": "declarative",
            "extractor": "attribute_date",
            "field": "properties.date",
            "format": "auto",
            "tz": "UTC",
        },
    }
