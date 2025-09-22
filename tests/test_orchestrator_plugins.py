"""Tests for orchestrator plugin integration."""

import tempfile
from pathlib import Path
from typing import Dict, Any

import pytest

from geoexhibit.analyzer import Analyzer, AnalyzerOutput, AssetSpec
from geoexhibit.config import GeoExhibitConfig, create_default_config
from geoexhibit.orchestrator import create_analyzer_from_config, create_publish_plan_from_config
from geoexhibit.plugin_registry import get_registry
from geoexhibit.timespan import TimeSpan


class MockAnalyzer(Analyzer):
    """Mock analyzer for testing."""
    
    def __init__(self, test_value: str = "default"):
        self.test_value = test_value
    
    def analyze(self, feature: Dict[str, Any], timespan: TimeSpan) -> AnalyzerOutput:
        feature_id = feature.get("properties", {}).get("feature_id", "unknown")
        return AnalyzerOutput(
            primary_cog_asset=AssetSpec(
                key="mock_analysis",
                href=f"/tmp/{feature_id}_mock.tif",
                title=f"Mock Analysis ({self.test_value})",
                roles=["data", "primary"],
            ),
            extra_properties={
                "mock:test_value": self.test_value,
                "mock:feature_id": feature_id,
            }
        )
    
    @property
    def name(self) -> str:
        return "mock_analyzer"


@pytest.fixture
def sample_features():
    """Sample feature collection for testing."""
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "feature_id": "test_feature_1",
                    "fire_date": "2023-09-15",
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[138.6, -34.9], [138.7, -34.9], [138.7, -34.8], [138.6, -34.8], [138.6, -34.9]]]
                }
            }
        ]
    }


@pytest.fixture
def base_config():
    """Base configuration for testing."""
    config_data = create_default_config()
    return GeoExhibitConfig(
        project=config_data["project"],
        aws=config_data["aws"],
        map=config_data["map"],
        stac=config_data["stac"],
        ids=config_data["ids"],
        time=config_data["time"],
        analyzer=config_data["analyzer"],
    )


class TestCreateAnalyzerFromConfig:
    """Test analyzer creation from configuration."""
    
    def setup_method(self):
        """Clean registry before each test."""
        # Clear the global registry for clean tests
        registry = get_registry()
        registry._analyzers.clear()
        registry._discovered_directories.clear()
    
    def test_create_builtin_demo_analyzer(self, base_config):
        """Test creating built-in demo analyzer."""
        base_config.analyzer["name"] = "demo_analyzer"
        
        analyzer = create_analyzer_from_config(base_config)
        
        # Should be a DemoAnalyzer instance
        assert analyzer.name == "demo_analyzer"
        assert hasattr(analyzer, "analyze")
    
    def test_create_analyzer_with_parameters(self, base_config):
        """Test creating analyzer with custom parameters."""
        # Register a mock analyzer
        registry = get_registry()
        registry.register("mock_analyzer")(MockAnalyzer)
        
        base_config.analyzer["name"] = "mock_analyzer"
        base_config.analyzer["parameters"] = {"test_value": "configured"}
        
        analyzer = create_analyzer_from_config(base_config)
        
        assert isinstance(analyzer, MockAnalyzer)
        assert analyzer.test_value == "configured"
    
    def test_create_analyzer_not_found(self, base_config):
        """Test error handling when analyzer not found."""
        base_config.analyzer["name"] = "nonexistent_analyzer"
        
        with pytest.raises(ValueError) as exc_info:
            create_analyzer_from_config(base_config)
        
        error_msg = str(exc_info.value)
        assert "Failed to create analyzer 'nonexistent_analyzer'" in error_msg
        assert "Available analyzers:" in error_msg
        assert "Make sure the plugin is installed" in error_msg
    
    def test_plugin_directory_discovery(self, base_config, caplog):
        """Test plugin discovery from configured directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create a plugin file
            plugin_file = temp_path / "test_plugin.py"
            plugin_content = '''
from geoexhibit.analyzer import Analyzer, AnalyzerOutput, AssetSpec
from geoexhibit.plugin_registry import get_registry

@get_registry().register("directory_test_analyzer")
class DirectoryTestAnalyzer(Analyzer):
    def analyze(self, feature, timespan):
        return AnalyzerOutput(
            primary_cog_asset=AssetSpec(key="test", href="/tmp/test.tif")
        )
    
    @property
    def name(self):
        return "directory_test_analyzer"
'''
            plugin_file.write_text(plugin_content)
            
            # Configure to use this directory
            base_config.analyzer["name"] = "directory_test_analyzer"
            base_config.analyzer["plugin_directories"] = [str(temp_path)]
            
            # Should discover and create the analyzer
            analyzer = create_analyzer_from_config(base_config)
            assert analyzer.name == "directory_test_analyzer"
            
            # Should have logged discovery
            assert f"Discovering plugins in {temp_path}" in caplog.text
    
    def test_nonexistent_plugin_directory_logged(self, base_config, caplog):
        """Test that nonexistent plugin directories are logged but don't fail."""
        base_config.analyzer["name"] = "demo_analyzer"  # Use built-in
        base_config.analyzer["plugin_directories"] = ["/nonexistent/path"]
        
        # Should still work with built-in analyzer
        analyzer = create_analyzer_from_config(base_config)
        assert analyzer.name == "demo_analyzer"
        
        # Should have logged the missing directory
        assert "does not exist, skipping" in caplog.text
    
    def test_multiple_plugin_directories(self, base_config):
        """Test discovery from multiple plugin directories."""
        with tempfile.TemporaryDirectory() as temp_dir1, tempfile.TemporaryDirectory() as temp_dir2:
            temp_path1 = Path(temp_dir1)
            temp_path2 = Path(temp_dir2)
            
            # Create plugins in both directories
            plugin1 = temp_path1 / "plugin1.py"
            plugin1.write_text('''
from geoexhibit.analyzer import Analyzer, AnalyzerOutput, AssetSpec
from geoexhibit.plugin_registry import get_registry

@get_registry().register("plugin1")
class Plugin1Analyzer(Analyzer):
    def analyze(self, feature, timespan):
        return AnalyzerOutput(primary_cog_asset=AssetSpec(key="test", href="/tmp/test.tif"))
    @property
    def name(self):
        return "plugin1"
''')
            
            plugin2 = temp_path2 / "plugin2.py"
            plugin2.write_text('''
from geoexhibit.analyzer import Analyzer, AnalyzerOutput, AssetSpec
from geoexhibit.plugin_registry import get_registry

@get_registry().register("plugin2")
class Plugin2Analyzer(Analyzer):
    def analyze(self, feature, timespan):
        return AnalyzerOutput(primary_cog_asset=AssetSpec(key="test", href="/tmp/test.tif"))
    @property
    def name(self):
        return "plugin2"
''')
            
            base_config.analyzer["name"] = "plugin2"
            base_config.analyzer["plugin_directories"] = [str(temp_path1), str(temp_path2)]
            
            # Should find and create plugin2
            analyzer = create_analyzer_from_config(base_config)
            assert analyzer.name == "plugin2"
            
            # Both plugins should be available in registry
            registry = get_registry()
            assert registry.get_analyzer("plugin1") is not None
            assert registry.get_analyzer("plugin2") is not None


class TestCreatePublishPlanFromConfig:
    """Test publish plan creation from configuration."""
    
    def setup_method(self):
        """Clean registry before each test."""
        registry = get_registry()
        registry._analyzers.clear()
        registry._discovered_directories.clear()
    
    def test_create_publish_plan_success(self, sample_features, base_config):
        """Test successful publish plan creation from config."""
        base_config.analyzer["name"] = "demo_analyzer"
        
        plan = create_publish_plan_from_config(sample_features, base_config)
        
        assert plan.collection_id == base_config.collection_id
        assert plan.item_count == 1
        assert plan.feature_count == 1
        assert len(plan.items) == 1
        
        item = plan.items[0]
        assert item.feature["properties"]["feature_id"] == "test_feature_1"
        assert item.analyzer_output.primary_cog_asset.key == "analysis"
    
    def test_create_publish_plan_with_plugin(self, sample_features, base_config):
        """Test publish plan creation with plugin analyzer."""
        # Register mock analyzer
        registry = get_registry()
        registry.register("mock_for_plan")(MockAnalyzer)
        
        base_config.analyzer["name"] = "mock_for_plan"
        base_config.analyzer["parameters"] = {"test_value": "plan_test"}
        
        plan = create_publish_plan_from_config(sample_features, base_config)
        
        assert plan.item_count == 1
        item = plan.items[0]
        
        # Should have used the mock analyzer
        assert item.analyzer_output.primary_cog_asset.key == "mock_analysis"
        assert item.analyzer_output.primary_cog_asset.title == "Mock Analysis (plan_test)"
        assert item.analyzer_output.extra_properties["mock:test_value"] == "plan_test"
    
    def test_create_publish_plan_analyzer_error(self, sample_features, base_config):
        """Test error handling when analyzer creation fails."""
        base_config.analyzer["name"] = "nonexistent_analyzer"
        
        with pytest.raises(ValueError, match="Failed to create analyzer"):
            create_publish_plan_from_config(sample_features, base_config)
    
    def test_create_publish_plan_empty_features(self, base_config):
        """Test error handling with empty feature collection."""
        empty_features = {"type": "FeatureCollection", "features": []}
        base_config.analyzer["name"] = "demo_analyzer"
        
        with pytest.raises(ValueError, match="FeatureCollection is empty"):
            create_publish_plan_from_config(empty_features, base_config)
    
    def test_create_publish_plan_invalid_features(self, base_config):
        """Test error handling with invalid feature collection."""
        invalid_features = {"type": "NotAFeatureCollection"}
        base_config.analyzer["name"] = "demo_analyzer"
        
        with pytest.raises(ValueError, match="Input must be a GeoJSON FeatureCollection"):
            create_publish_plan_from_config(invalid_features, base_config)