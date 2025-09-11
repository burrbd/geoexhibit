"""Tests for orchestrator functionality."""

from datetime import datetime, timezone

from geoexhibit.analyzer import AssetSpec, AnalyzerOutput, Analyzer
from geoexhibit.config import GeoExhibitConfig, validate_config
from geoexhibit.orchestrator import create_publish_plan
from geoexhibit.time_provider import ConstantTimeProvider


class TestAnalyzer(Analyzer):
    """Test analyzer for orchestrator testing."""

    @property
    def name(self) -> str:
        return "test-analyzer"

    def analyze(self, feature, timespan) -> AnalyzerOutput:
        return AnalyzerOutput(
            primary_cog_asset=AssetSpec(key="test-cog", href="/test.tif")
        )


def test_create_publish_plan_basic():
    """Test basic publish plan creation."""
    features = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"feature_id": "feat-1", "name": "Test Feature"},
                "geometry": {"type": "Point", "coordinates": [0, 0]},
            }
        ],
    }

    config = _create_test_config()
    analyzer = TestAnalyzer()
    time_provider = ConstantTimeProvider(datetime(2023, 9, 15, tzinfo=timezone.utc))

    plan = create_publish_plan(features, analyzer, config, time_provider)

    assert plan.collection_id == "test_collection"
    assert plan.item_count == 1
    assert plan.feature_count == 1
    assert len(plan.job_id) > 0  # Should have a generated ULID


def test_create_publish_plan_multiple_features():
    """Test publish plan creation with multiple features."""
    features = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"feature_id": "feat-1"},
                "geometry": {"type": "Point", "coordinates": [0, 0]},
            },
            {
                "type": "Feature",
                "properties": {"feature_id": "feat-2"},
                "geometry": {"type": "Point", "coordinates": [1, 1]},
            },
        ],
    }

    config = _create_test_config()
    analyzer = TestAnalyzer()
    time_provider = ConstantTimeProvider(datetime(2023, 9, 15, tzinfo=timezone.utc))

    plan = create_publish_plan(features, analyzer, config, time_provider)

    assert plan.item_count == 2
    assert plan.feature_count == 2


def test_create_publish_plan_time_provider_from_config():
    """Test publish plan creation using time provider from config."""
    features = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"fire_date": "2023-09-15"},
                "geometry": {"type": "Point", "coordinates": [0, 0]},
            }
        ],
    }

    config = _create_test_config()
    analyzer = TestAnalyzer()

    plan = create_publish_plan(features, analyzer, config)

    assert plan.item_count == 1
    assert plan.items[0].timespan.start.year == 2023
    assert plan.items[0].timespan.start.month == 9
    assert plan.items[0].timespan.start.day == 15


def test_create_publish_plan_missing_feature_id():
    """Test plan creation adds feature_id when missing."""
    features = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"name": "Test Feature"},
                "geometry": {"type": "Point", "coordinates": [0, 0]},
            }
        ],
    }

    config = _create_test_config()
    analyzer = TestAnalyzer()
    time_provider = ConstantTimeProvider(datetime(2023, 9, 15, tzinfo=timezone.utc))

    plan = create_publish_plan(features, analyzer, config, time_provider)

    assert plan.item_count == 1
    feature_id = plan.items[0].feature_id
    assert len(feature_id) > 0  # Should have generated a feature_id


def test_create_publish_plan_invalid_input():
    """Test error handling for invalid inputs."""
    config = _create_test_config()
    analyzer = TestAnalyzer()
    time_provider = ConstantTimeProvider(datetime(2023, 9, 15, tzinfo=timezone.utc))

    # Invalid feature collection type
    try:
        create_publish_plan({"type": "Feature"}, analyzer, config, time_provider)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "FeatureCollection" in str(e)

    # Empty feature collection
    try:
        empty_features = {"type": "FeatureCollection", "features": []}
        create_publish_plan(empty_features, analyzer, config, time_provider)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "empty" in str(e)


def _create_test_config() -> GeoExhibitConfig:
    """Create a test configuration."""
    config_data = {
        "project": {
            "name": "test-project",
            "collection_id": "test_collection",
            "title": "Test Collection",
            "description": "Test description",
        },
        "aws": {"s3_bucket": "test-bucket"},
        "map": {"pmtiles": {"feature_id_property": "feature_id"}},
        "stac": {"use_extensions": ["proj"]},
        "ids": {"strategy": "ulid", "prefix": "test"},
        "time": {
            "mode": "declarative",
            "extractor": "attribute_date",
            "field": "properties.fire_date",
        },
    }

    return validate_config(config_data)
