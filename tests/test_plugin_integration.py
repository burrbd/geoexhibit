"""Integration tests for the plugin system with config and pipeline."""

import tempfile
from pathlib import Path
import json
import pytest

from geoexhibit.config import validate_config, create_default_config
from geoexhibit.plugin_registry import register, get_analyzer, PluginNotFoundError
from geoexhibit.analyzer import Analyzer, AnalyzerOutput, AssetSpec
from geoexhibit.timespan import TimeSpan
from geoexhibit.pipeline import run_geoexhibit_pipeline
from typing import Dict, Any


# Test analyzer for integration tests
@register("integration_test")
class IntegrationTestAnalyzer(Analyzer):
    """Test analyzer for integration testing."""

    def __init__(self, output_dir=None):
        self.output_dir = Path(output_dir or tempfile.mkdtemp())
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @property
    def name(self) -> str:
        return "integration_test_analyzer"

    def analyze(self, feature: Dict[str, Any], timespan: TimeSpan) -> AnalyzerOutput:
        # Create a simple test file
        test_file = self.output_dir / f"test_{feature['properties']['feature_id']}.tif"
        test_file.touch()

        return AnalyzerOutput(
            primary_cog_asset=AssetSpec(
                key="analysis",
                href=str(test_file),
                title="Integration Test Analysis",
                description="Test analysis for plugin integration",
                media_type="image/tiff; application=geotiff; profile=cloud-optimized",
                roles=["data", "primary"],
            ),
            extra_properties={
                "geoexhibit:analyzer": self.name,
                "integration:test_mode": True,
            },
        )


def test_config_analyzer_section_validation():
    """Test that analyzer section is properly validated in config."""
    # Test default analyzer configuration
    config_data = create_default_config()
    assert "analyzer" in config_data
    assert config_data["analyzer"]["name"] == "demo"

    config = validate_config(config_data)
    assert config.analyzer_name == "demo"
    assert config.analyzer_config["name"] == "demo"


def test_config_custom_analyzer():
    """Test config with custom analyzer selection."""
    config_data = create_default_config()
    config_data["analyzer"]["name"] = "integration_test"

    config = validate_config(config_data)
    assert config.analyzer_name == "integration_test"


def test_config_without_analyzer_section():
    """Test that config defaults to demo analyzer when section missing."""
    config_data = create_default_config()
    del config_data["analyzer"]  # Remove analyzer section

    config = validate_config(config_data)
    assert config.analyzer_name == "demo"  # Should default to demo


def test_config_analyzer_validation_errors():
    """Test analyzer configuration validation errors."""
    config_data = create_default_config()

    # Test non-string analyzer name
    config_data["analyzer"]["name"] = 123
    with pytest.raises(ValueError, match="Analyzer name must be a string"):
        validate_config(config_data)


def test_pipeline_plugin_selection():
    """Test that pipeline correctly selects analyzer from config."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create test features file
        features_file = temp_path / "features.json"
        features = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"name": "Test Feature", "fire_date": "2023-09-15"},
                    "geometry": {"type": "Point", "coordinates": [138.6, -34.9]},
                }
            ],
        }
        with open(features_file, "w") as f:
            json.dump(features, f)

        # Create config with integration test analyzer
        config_data = create_default_config()
        config_data["analyzer"]["name"] = "integration_test"
        config = validate_config(config_data)

        # Run pipeline with local output
        local_out = temp_path / "output"
        result = run_geoexhibit_pipeline(
            config=config,
            features_file=features_file,
            local_out_dir=local_out,
            dry_run=True,  # Don't actually publish for this test
        )

        assert result["job_id"]
        assert result["item_count"] == 1
        assert result["dry_run"] is True


def test_pipeline_analyzer_not_found():
    """Test pipeline behavior when analyzer plugin not found."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create test features file
        features_file = temp_path / "features.json"
        features = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"fire_date": "2023-09-15"},
                    "geometry": {"type": "Point", "coordinates": [138.6, -34.9]},
                }
            ],
        }
        with open(features_file, "w") as f:
            json.dump(features, f)

        # Create config with nonexistent analyzer
        config_data = create_default_config()
        config_data["analyzer"]["name"] = "nonexistent_analyzer"
        config = validate_config(config_data)

        # Pipeline should raise PluginNotFoundError
        local_out = temp_path / "output"
        with pytest.raises(PluginNotFoundError):
            run_geoexhibit_pipeline(
                config=config,
                features_file=features_file,
                local_out_dir=local_out,
                dry_run=True,
            )


def test_demo_analyzer_backward_compatibility():
    """Test that demo analyzer still works for backward compatibility."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create test features file
        features_file = temp_path / "features.json"
        features = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"fire_date": "2023-09-15"},
                    "geometry": {"type": "Point", "coordinates": [138.6, -34.9]},
                }
            ],
        }
        with open(features_file, "w") as f:
            json.dump(features, f)

        # Create config with demo analyzer (default)
        config_data = create_default_config()
        assert config_data["analyzer"]["name"] == "demo"
        config = validate_config(config_data)

        # Should work without errors
        local_out = temp_path / "output"
        result = run_geoexhibit_pipeline(
            config=config,
            features_file=features_file,
            local_out_dir=local_out,
            dry_run=True,
        )

        assert result["job_id"]
        assert result["item_count"] == 1


def test_analyzer_parameters_via_config():
    """Test passing parameters to analyzers via config."""
    # Test that analyzers can receive parameters
    # (For now, this is a placeholder - we could extend config to support analyzer params)

    @register("parameterized_test")
    class ParameterizedAnalyzer(Analyzer):
        def __init__(self, custom_param="default"):
            self.custom_param = custom_param

        @property
        def name(self) -> str:
            return "parameterized"

        def analyze(
            self, feature: Dict[str, Any], timespan: TimeSpan
        ) -> AnalyzerOutput:
            return AnalyzerOutput(
                primary_cog_asset=AssetSpec(
                    key="test", href="/tmp/test.tif", roles=["data", "primary"]
                ),
                extra_properties={"custom_param": self.custom_param},
            )

    # Test basic instantiation (parameters could be added to config in future)
    analyzer = get_analyzer("parameterized_test", custom_param="custom_value")
    assert analyzer.custom_param == "custom_value"


def test_multiple_analyzer_registration():
    """Test that multiple analyzers can coexist."""

    @register("multi_test_1")
    class MultiTest1(Analyzer):
        @property
        def name(self) -> str:
            return "multi1"

        def analyze(
            self, feature: Dict[str, Any], timespan: TimeSpan
        ) -> AnalyzerOutput:
            return AnalyzerOutput(
                primary_cog_asset=AssetSpec(
                    key="m1", href="/tmp/m1.tif", roles=["data"]
                )
            )

    @register("multi_test_2")
    class MultiTest2(Analyzer):
        @property
        def name(self) -> str:
            return "multi2"

        def analyze(
            self, feature: Dict[str, Any], timespan: TimeSpan
        ) -> AnalyzerOutput:
            return AnalyzerOutput(
                primary_cog_asset=AssetSpec(
                    key="m2", href="/tmp/m2.tif", roles=["data"]
                )
            )

    # Both should be available
    analyzer1 = get_analyzer("multi_test_1")
    analyzer2 = get_analyzer("multi_test_2")

    assert analyzer1.name == "multi1"
    assert analyzer2.name == "multi2"


def test_config_json_example():
    """Test loading config from JSON with analyzer specification."""
    config_json = {
        "project": {
            "name": "test-project",
            "collection_id": "test_collection",
            "title": "Test Collection",
            "description": "Test description",
        },
        "aws": {"s3_bucket": "test-bucket", "region": "us-east-1"},
        "map": {"pmtiles": {"minzoom": 5, "maxzoom": 14}, "base_url": ""},
        "stac": {"use_extensions": ["proj", "raster"], "geometry_in_item": True},
        "ids": {"strategy": "ulid"},
        "time": {
            "mode": "declarative",
            "extractor": "attribute_date",
            "field": "properties.fire_date",
            "format": "auto",
            "tz": "UTC",
        },
        "analyzer": {"name": "integration_test"},
    }

    config = validate_config(config_json)
    assert config.analyzer_name == "integration_test"
    assert config.project_name == "test-project"
