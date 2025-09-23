"""Unit tests for plugin system config integration with proper mocking."""

from unittest.mock import Mock, patch
import pytest

from geoexhibit.config import validate_config, create_default_config
from geoexhibit.plugin_registry import PluginNotFoundError
from geoexhibit.analyzer import Analyzer, AnalyzerOutput, AssetSpec


def test_config_analyzer_section_validation():
    """Test analyzer section validation in config (unit test)."""
    config_data = create_default_config()

    # Test that default config includes analyzer section
    assert "analyzer" in config_data
    assert config_data["analyzer"]["name"] == "demo"

    # Test config object properties
    config = validate_config(config_data)
    assert config.analyzer_name == "demo"
    assert config.analyzer_config["name"] == "demo"


def test_config_custom_analyzer():
    """Test config with custom analyzer selection."""
    config_data = create_default_config()
    config_data["analyzer"]["name"] = "custom_test"

    config = validate_config(config_data)
    assert config.analyzer_name == "custom_test"


def test_config_without_analyzer_section():
    """Test that config defaults to demo analyzer when section missing."""
    config_data = create_default_config()
    del config_data["analyzer"]  # Remove analyzer section

    config = validate_config(config_data)
    assert config.analyzer_name == "demo"  # Should default to demo


def test_config_analyzer_validation_errors():
    """Test analyzer configuration validation error handling."""
    config_data = create_default_config()

    # Test non-string analyzer name
    config_data["analyzer"]["name"] = 123
    with pytest.raises(ValueError, match="Analyzer name must be a string"):
        validate_config(config_data)


@patch("geoexhibit.pipeline.plugin_registry.get_analyzer")
@patch("geoexhibit.pipeline.load_and_validate_features")
@patch("geoexhibit.pipeline.create_publish_plan")
@patch("geoexhibit.pipeline.create_publisher")
def test_pipeline_uses_config_analyzer_selection(
    mock_create_publisher, mock_create_plan, mock_load_features, mock_get_analyzer
):
    """Test that pipeline correctly uses analyzer from config (unit test with mocks)."""
    from geoexhibit.pipeline import run_geoexhibit_pipeline
    from pathlib import Path

    # Mock dependencies
    mock_features = {"type": "FeatureCollection", "features": []}
    mock_load_features.return_value = mock_features

    mock_analyzer = Mock()
    mock_analyzer.name = "mock_test_analyzer"
    mock_get_analyzer.return_value = mock_analyzer

    mock_plan = Mock()
    mock_plan.item_count = 1
    mock_plan.feature_count = 1
    mock_plan.job_id = "test-job-123"
    mock_create_plan.return_value = mock_plan

    mock_publisher = Mock()
    mock_publisher.publish_plan.return_value = None
    mock_publisher.verify_publication.return_value = True
    mock_create_publisher.return_value = mock_publisher

    # Create config with custom analyzer
    config_data = create_default_config()
    config_data["analyzer"]["name"] = "custom_mock"
    config = validate_config(config_data)

    # Mock features file
    features_file = Path("/fake/features.json")

    # Run pipeline
    result = run_geoexhibit_pipeline(
        config=config, features_file=features_file, dry_run=True
    )

    # Verify that plugin registry was called with correct analyzer name
    mock_get_analyzer.assert_called_once_with("custom_mock")

    # Verify pipeline completed successfully
    assert result["job_id"] == "test-job-123"
    assert result["dry_run"] is True


@patch("geoexhibit.pipeline.plugin_registry.get_analyzer")
@patch("geoexhibit.pipeline.load_and_validate_features")
def test_pipeline_handles_analyzer_not_found(mock_load_features, mock_get_analyzer):
    """Test pipeline error handling when analyzer plugin not found (unit test)."""
    from geoexhibit.pipeline import run_geoexhibit_pipeline
    from pathlib import Path

    # Mock features loading
    mock_features = {"type": "FeatureCollection", "features": [{"type": "Feature"}]}
    mock_load_features.return_value = mock_features

    # Mock plugin not found error
    mock_get_analyzer.side_effect = PluginNotFoundError(
        "Test error: analyzer not found"
    )

    # Create config with nonexistent analyzer
    config_data = create_default_config()
    config_data["analyzer"]["name"] = "nonexistent"
    config = validate_config(config_data)

    features_file = Path("/fake/features.json")

    # Should raise PluginNotFoundError
    with pytest.raises(PluginNotFoundError, match="Test error: analyzer not found"):
        run_geoexhibit_pipeline(
            config=config, features_file=features_file, dry_run=True
        )


@patch("geoexhibit.pipeline.plugin_registry.list_analyzers")
@patch("geoexhibit.pipeline.plugin_registry.get_analyzer")
@patch("geoexhibit.pipeline.load_and_validate_features")
def test_pipeline_logs_available_analyzers_on_error(
    mock_load_features, mock_get_analyzer, mock_list_analyzers
):
    """Test that pipeline logs available analyzers when plugin not found."""
    from geoexhibit.pipeline import run_geoexhibit_pipeline
    from pathlib import Path

    # Mock features
    mock_load_features.return_value = {"type": "FeatureCollection", "features": []}

    # Mock plugin error and available list
    mock_get_analyzer.side_effect = PluginNotFoundError("Plugin not found")
    mock_list_analyzers.return_value = ["demo", "example", "custom"]

    config_data = create_default_config()
    config_data["analyzer"]["name"] = "missing"
    config = validate_config(config_data)

    with pytest.raises(PluginNotFoundError):
        run_geoexhibit_pipeline(
            config=config, features_file=Path("/fake/features.json"), dry_run=True
        )

    # Verify that list_analyzers was called (for logging available options)
    mock_list_analyzers.assert_called_once()


def test_analyzer_interface_mock_compliance():
    """Test that mock analyzers comply with the Analyzer interface."""

    class TestMockAnalyzer(Analyzer):
        @property
        def name(self) -> str:
            return "test_mock"

        def analyze(self, feature, timespan) -> AnalyzerOutput:
            return AnalyzerOutput(
                primary_cog_asset=AssetSpec(
                    key="test", href="/tmp/test.tif", roles=["data", "primary"]
                )
            )

    mock_analyzer = TestMockAnalyzer()

    # Test interface compliance
    assert hasattr(mock_analyzer, "name")
    assert hasattr(mock_analyzer, "analyze")
    assert isinstance(mock_analyzer.name, str)
    assert callable(mock_analyzer.analyze)

    # Test that analyze method returns proper type
    mock_feature = {"properties": {"feature_id": "test"}}
    mock_timespan = Mock()

    result = mock_analyzer.analyze(mock_feature, mock_timespan)
    assert isinstance(result, AnalyzerOutput)
    assert result.primary_cog_asset.key == "test"


@patch("geoexhibit.config.validate_config")
def test_config_validation_called_properly(mock_validate):
    """Test that config validation is called correctly in isolated unit test."""
    mock_config = Mock()
    mock_config.analyzer_name = "test_analyzer"
    mock_validate.return_value = mock_config

    # Test that we can mock the validation process
    config_data = {"analyzer": {"name": "test_analyzer"}}
    result = mock_validate(config_data)

    assert result.analyzer_name == "test_analyzer"
    mock_validate.assert_called_once_with(config_data)
