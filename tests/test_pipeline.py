"""Tests for main pipeline orchestration."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from geoexhibit.config import GeoExhibitConfig, validate_config
from geoexhibit.pipeline import (
    create_example_features,
    ensure_feature_ids,
    load_and_validate_features,
    load_ndjson_features,
    run_geoexhibit_pipeline,
    validate_feature_collection,
)


def test_create_example_features():
    """Test example features generation."""
    features = create_example_features()

    assert features["type"] == "FeatureCollection"
    assert len(features["features"]) == 3

    for feature in features["features"]:
        assert feature["type"] == "Feature"
        assert "properties" in feature
        assert "geometry" in feature
        assert "fire_date" in feature["properties"]


def test_validate_feature_collection_valid():
    """Test feature collection validation with valid data."""
    valid_features = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"name": "Test"},
                "geometry": {"type": "Point", "coordinates": [0, 0]},
            }
        ],
    }

    validate_feature_collection(valid_features)  # Should not raise


def test_validate_feature_collection_invalid_type():
    """Test feature collection validation with invalid type."""
    invalid_features = {"type": "Feature"}

    try:
        validate_feature_collection(invalid_features)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "FeatureCollection" in str(e)


def test_validate_feature_collection_missing_geometry():
    """Test feature collection validation with missing geometry."""
    invalid_features = {
        "type": "FeatureCollection",
        "features": [{"type": "Feature", "properties": {}}],
    }

    try:
        validate_feature_collection(invalid_features)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "geometry" in str(e)


def test_ensure_feature_ids():
    """Test feature ID generation for features without IDs."""
    features = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {},
                "geometry": {"type": "Point", "coordinates": [0, 0]},
            },
            {
                "type": "Feature",
                "properties": {"feature_id": "existing-id"},
                "geometry": {"type": "Point", "coordinates": [1, 1]},
            },
        ],
    }

    ensure_feature_ids(features)

    # First feature should get a generated ID
    assert "feature_id" in features["features"][0]["properties"]
    assert len(features["features"][0]["properties"]["feature_id"]) > 0

    # Second feature should keep existing ID
    assert features["features"][1]["properties"]["feature_id"] == "existing-id"


def test_load_and_validate_features_geojson():
    """Test loading GeoJSON features."""
    features_data = create_example_features()

    with tempfile.NamedTemporaryFile(mode="w", suffix=".geojson", delete=False) as f:
        json.dump(features_data, f)
        temp_path = Path(f.name)

    try:
        loaded_features = load_and_validate_features(temp_path)

        assert loaded_features["type"] == "FeatureCollection"
        assert len(loaded_features["features"]) == 3

        # Should have ensured feature IDs
        for feature in loaded_features["features"]:
            assert "feature_id" in feature["properties"]

    finally:
        temp_path.unlink()


def test_load_and_validate_features_ndjson():
    """Test loading NDJSON features."""
    features = create_example_features()["features"]

    with tempfile.NamedTemporaryFile(mode="w", suffix=".ndjson", delete=False) as f:
        for feature in features:
            json.dump(feature, f)
            f.write("\n")
        temp_path = Path(f.name)

    try:
        loaded_features = load_and_validate_features(temp_path)

        assert loaded_features["type"] == "FeatureCollection"
        assert len(loaded_features["features"]) == 3

    finally:
        temp_path.unlink()


def test_load_ndjson_features():
    """Test NDJSON loading with mixed content."""
    ndjson_content = """{"type": "Feature", "properties": {"id": 1}, "geometry": {"type": "Point", "coordinates": [0, 0]}}
{"type": "Feature", "properties": {"id": 2}, "geometry": {"type": "Point", "coordinates": [1, 1]}}
{"type": "NotFeature", "data": "skip this"}

{"type": "Feature", "properties": {"id": 3}, "geometry": {"type": "Point", "coordinates": [2, 2]}}
invalid json line
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".ndjson", delete=False) as f:
        f.write(ndjson_content)
        temp_path = Path(f.name)

    try:
        result = load_ndjson_features(temp_path)

        assert result["type"] == "FeatureCollection"
        assert len(result["features"]) == 3  # Only valid features

        assert result["features"][0]["properties"]["id"] == 1
        assert result["features"][1]["properties"]["id"] == 2
        assert result["features"][2]["properties"]["id"] == 3

    finally:
        temp_path.unlink()


def test_load_and_validate_features_file_not_found():
    """Test error handling when features file doesn't exist."""
    try:
        load_and_validate_features(Path("/nonexistent/file.geojson"))
        assert False, "Should have raised FileNotFoundError"
    except FileNotFoundError:
        pass


def test_load_and_validate_features_unsupported_format():
    """Test error handling for unsupported file formats."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("not geospatial data")
        temp_path = Path(f.name)

    try:
        load_and_validate_features(temp_path)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Unsupported file format" in str(e)
    finally:
        temp_path.unlink()


@patch("geoexhibit.pipeline.create_publisher")
@patch("geoexhibit.pipeline.generate_pmtiles_plan")
def test_run_geoexhibit_pipeline_dry_run(mock_generate_pmtiles, mock_create_publisher):
    """Test running pipeline in dry-run mode."""
    mock_publisher = mock_create_publisher.return_value
    mock_generate_pmtiles.return_value = "/tmp/features.pmtiles"

    config = _create_test_config()

    with tempfile.NamedTemporaryFile(mode="w", suffix=".geojson", delete=False) as f:
        json.dump(create_example_features(), f)
        features_file = Path(f.name)

    try:
        result = run_geoexhibit_pipeline(config, features_file, dry_run=True)

        assert result["dry_run"] is True
        assert result["item_count"] == 3  # 3 features with 1 time each
        assert result["feature_count"] == 3
        assert result["output_type"] == "s3"
        assert "job_id" in result

        # Publisher should be created but not called for actual publishing
        mock_create_publisher.assert_called_once()
        mock_publisher.publish_plan.assert_not_called()

    finally:
        features_file.unlink()


@patch("geoexhibit.pipeline.create_publisher")
@patch("geoexhibit.pipeline.generate_pmtiles_plan")
def test_run_geoexhibit_pipeline_local_output(
    mock_generate_pmtiles, mock_create_publisher
):
    """Test running pipeline with local output."""
    mock_publisher = mock_create_publisher.return_value
    mock_publisher.verify_publication.return_value = True
    mock_generate_pmtiles.return_value = "/tmp/features.pmtiles"

    config = _create_test_config()

    with tempfile.TemporaryDirectory() as temp_dir:
        output_dir = Path(temp_dir) / "output"

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".geojson", delete=False
        ) as f:
            json.dump(create_example_features(), f)
            features_file = Path(f.name)

        try:
            result = run_geoexhibit_pipeline(
                config, features_file, local_out_dir=output_dir
            )

            assert result["dry_run"] is False
            assert result["output_type"] == "local"
            assert result["verification_passed"] is True

            mock_publisher.publish_plan.assert_called_once()
            mock_publisher.verify_publication.assert_called_once()

        finally:
            features_file.unlink()


@patch("geoexhibit.pipeline.create_publisher")
@patch("geoexhibit.pipeline.generate_pmtiles_plan")
def test_run_geoexhibit_pipeline_pmtiles_failure(
    mock_generate_pmtiles, mock_create_publisher
):
    """Test pipeline continues when PMTiles generation fails."""
    mock_publisher = mock_create_publisher.return_value
    mock_publisher.verify_publication.return_value = True
    mock_generate_pmtiles.side_effect = RuntimeError("tippecanoe not found")

    config = _create_test_config()

    with tempfile.NamedTemporaryFile(mode="w", suffix=".geojson", delete=False) as f:
        json.dump(create_example_features(), f)
        features_file = Path(f.name)

    try:
        result = run_geoexhibit_pipeline(config, features_file, dry_run=True)

        # Pipeline should continue despite PMTiles failure
        assert result["pmtiles_generated"] is False
        assert "job_id" in result

    finally:
        features_file.unlink()


def _create_test_config() -> GeoExhibitConfig:
    """Create a test configuration."""
    config_data = {
        "project": {
            "name": "test-pipeline",
            "collection_id": "test_collection",
            "title": "Test Collection",
            "description": "Test description",
        },
        "aws": {"s3_bucket": "test-bucket"},
        "map": {"pmtiles": {"feature_id_property": "feature_id"}},
        "stac": {"use_extensions": ["proj"]},
        "ids": {"strategy": "ulid"},
        "time": {
            "mode": "declarative",
            "extractor": "attribute_date",
            "field": "properties.fire_date",
        },
    }
    return validate_config(config_data)
