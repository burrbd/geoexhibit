"""Tests for the plugin registry system."""

import tempfile
from pathlib import Path
from typing import Dict, Any

import pytest

from geoexhibit.analyzer import Analyzer, AnalyzerOutput, AssetSpec
from geoexhibit.plugin_registry import PluginRegistry, get_registry, register
from geoexhibit.timespan import TimeSpan


class TestAnalyzer(Analyzer):
    """Test analyzer for validation tests."""
    
    def __init__(self, test_param: str = "default"):
        self.test_param = test_param
    
    def analyze(self, feature: Dict[str, Any], timespan: TimeSpan) -> AnalyzerOutput:
        return AnalyzerOutput(
            primary_cog_asset=AssetSpec(
                key="test",
                href="/tmp/test.tif",
                title="Test Asset",
            )
        )
    
    @property
    def name(self) -> str:
        return "test_analyzer"


class InvalidAnalyzer:
    """Analyzer that doesn't inherit from Analyzer interface."""
    
    def analyze(self, feature: Dict[str, Any], timespan: TimeSpan) -> AnalyzerOutput:
        pass


class TestPluginRegistry:
    """Test cases for PluginRegistry class."""
    
    def setup_method(self):
        """Set up each test with a fresh registry."""
        self.registry = PluginRegistry()
    
    def test_register_decorator_success(self):
        """Test successful analyzer registration."""
        @self.registry.register("test_analyzer")
        class LocalTestAnalyzer(TestAnalyzer):
            pass
        
        # Should be registered
        analyzer_class = self.registry.get_analyzer("test_analyzer")
        assert analyzer_class is not None
        assert analyzer_class == LocalTestAnalyzer
    
    def test_register_invalid_class_fails(self):
        """Test that registering non-Analyzer class fails."""
        with pytest.raises(ValueError, match="must inherit from Analyzer"):
            @self.registry.register("invalid")
            class InvalidClass:
                pass
    
    def test_register_duplicate_name_warns(self, caplog):
        """Test that duplicate registration generates warning."""
        @self.registry.register("duplicate")
        class FirstAnalyzer(TestAnalyzer):
            pass
        
        @self.registry.register("duplicate")
        class SecondAnalyzer(TestAnalyzer):
            pass
        
        # Should have warning about overwriting
        assert "already registered, overwriting" in caplog.text
        
        # Should have the second analyzer
        analyzer_class = self.registry.get_analyzer("duplicate")
        assert analyzer_class == SecondAnalyzer
    
    def test_get_nonexistent_analyzer(self):
        """Test getting analyzer that doesn't exist."""
        result = self.registry.get_analyzer("nonexistent")
        assert result is None
    
    def test_list_analyzers(self):
        """Test listing all registered analyzers."""
        @self.registry.register("analyzer1")
        class Analyzer1(TestAnalyzer):
            pass
        
        @self.registry.register("analyzer2")
        class Analyzer2(TestAnalyzer):
            pass
        
        analyzers = self.registry.list_analyzers()
        assert len(analyzers) == 2
        assert "analyzer1" in analyzers
        assert "analyzer2" in analyzers
        assert analyzers["analyzer1"] == Analyzer1
        assert analyzers["analyzer2"] == Analyzer2
    
    def test_create_analyzer_success(self):
        """Test successful analyzer creation."""
        @self.registry.register("test_create")
        class CreateTestAnalyzer(TestAnalyzer):
            pass
        
        analyzer = self.registry.create_analyzer("test_create", test_param="custom")
        assert isinstance(analyzer, CreateTestAnalyzer)
        assert analyzer.test_param == "custom"
    
    def test_create_analyzer_not_found(self):
        """Test creating non-existent analyzer fails with helpful message."""
        @self.registry.register("existing")
        class ExistingAnalyzer(TestAnalyzer):
            pass
        
        with pytest.raises(ValueError) as exc_info:
            self.registry.create_analyzer("missing")
        
        error_msg = str(exc_info.value)
        assert "Analyzer 'missing' not found" in error_msg
        assert "Available analyzers: ['existing']" in error_msg
        assert "Ensure the plugin is installed and discoverable" in error_msg
    
    def test_create_analyzer_constructor_error(self):
        """Test analyzer creation with constructor errors."""
        @self.registry.register("constructor_error")
        class ConstructorErrorAnalyzer(Analyzer):
            def __init__(self, required_param: str):
                if not required_param:
                    raise ValueError("required_param cannot be empty")
                self.required_param = required_param
            
            def analyze(self, feature: Dict[str, Any], timespan: TimeSpan) -> AnalyzerOutput:
                return AnalyzerOutput(
                    primary_cog_asset=AssetSpec(key="test", href="/tmp/test.tif")
                )
            
            @property
            def name(self) -> str:
                return "constructor_error"
        
        with pytest.raises(ValueError) as exc_info:
            self.registry.create_analyzer("constructor_error")
        
        error_msg = str(exc_info.value)
        assert "Failed to create analyzer 'constructor_error'" in error_msg
        assert "Check the analyzer's constructor requirements" in error_msg
    
    def test_discover_plugins_nonexistent_directory(self, caplog):
        """Test plugin discovery with non-existent directory."""
        self.registry.discover_plugins(Path("/nonexistent/path"))
        assert "does not exist, skipping" in caplog.text
    
    def test_discover_plugins_empty_directory(self, caplog):
        """Test plugin discovery with empty directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            self.registry.discover_plugins(temp_path)
            assert "No Python files found" in caplog.text
    
    def test_discover_plugins_valid_plugin(self, caplog):
        """Test plugin discovery with valid plugin file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create a valid plugin file
            plugin_file = temp_path / "valid_plugin.py"
            plugin_content = '''
from geoexhibit.analyzer import Analyzer, AnalyzerOutput, AssetSpec
from geoexhibit.plugin_registry import get_registry

@get_registry().register("discovered_analyzer")
class DiscoveredAnalyzer(Analyzer):
    def analyze(self, feature, timespan):
        return AnalyzerOutput(
            primary_cog_asset=AssetSpec(key="test", href="/tmp/test.tif")
        )
    
    @property
    def name(self):
        return "discovered_analyzer"
'''
            plugin_file.write_text(plugin_content)
            
            # Discover plugins
            self.registry.discover_plugins(temp_path)
            
            # Should have loaded the plugin
            analyzer_class = self.registry.get_analyzer("discovered_analyzer")
            assert analyzer_class is not None
            assert "Successfully loaded plugin module" in caplog.text
    
    def test_discover_plugins_invalid_syntax(self, caplog):
        """Test plugin discovery with invalid Python syntax."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create invalid plugin file
            plugin_file = temp_path / "invalid_syntax.py"
            plugin_file.write_text("invalid python syntax @@@ !!!")
            
            # Discover plugins (should log error but not crash)
            self.registry.discover_plugins(temp_path)
            
            assert "Failed to load plugin" in caplog.text
    
    def test_discover_plugins_skip_private_modules(self, caplog):
        """Test that private modules (starting with _) are skipped."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create a private module
            plugin_file = temp_path / "_private_module.py"
            plugin_file.write_text("# This should be skipped")
            
            # Discover plugins
            self.registry.discover_plugins(temp_path)
            
            # Should not have tried to load it
            assert "_private_module" not in caplog.text
    
    def test_discover_plugins_duplicate_discovery(self, caplog):
        """Test that same directory isn't discovered twice."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # First discovery
            self.registry.discover_plugins(temp_path)
            
            # Second discovery
            self.registry.discover_plugins(temp_path)
            
            # Should skip second time
            assert "already discovered, skipping" in caplog.text
    
    def test_validate_plugin_success(self):
        """Test successful plugin validation."""
        # Should not raise an exception
        self.registry.validate_plugin(TestAnalyzer)
    
    def test_validate_plugin_not_analyzer_subclass(self):
        """Test validation fails for non-Analyzer subclass."""
        with pytest.raises(ValueError, match="must inherit from Analyzer"):
            self.registry.validate_plugin(InvalidAnalyzer)
    
    def test_validate_plugin_missing_analyze_method(self):
        """Test validation fails for missing analyze method."""
        class MissingAnalyzeMethod(Analyzer):
            @property
            def name(self):
                return "missing_analyze"
        
        with pytest.raises(ValueError, match="missing required method: analyze"):
            self.registry.validate_plugin(MissingAnalyzeMethod)
    
    def test_validate_plugin_missing_name_property(self):
        """Test validation fails for missing name property."""
        class MissingNameProperty(Analyzer):
            def analyze(self, feature, timespan):
                pass
        
        with pytest.raises(ValueError, match="missing required method: name"):
            self.registry.validate_plugin(MissingNameProperty)
    
    def test_validate_plugin_analyze_not_callable(self):
        """Test validation fails if analyze is not callable."""
        class NonCallableAnalyze(Analyzer):
            analyze = "not callable"
            
            @property
            def name(self):
                return "non_callable"
        
        with pytest.raises(ValueError, match="analyze must be callable"):
            self.registry.validate_plugin(NonCallableAnalyze)
    
    def test_validate_plugin_wrong_analyze_signature(self):
        """Test validation fails for wrong analyze method signature."""
        class WrongSignature(Analyzer):
            def analyze(self, wrong_param):  # Wrong signature
                pass
            
            @property
            def name(self):
                return "wrong_signature"
        
        with pytest.raises(ValueError, match="must have signature"):
            self.registry.validate_plugin(WrongSignature)


class TestGlobalRegistry:
    """Test cases for global registry functions."""
    
    def test_global_register_decorator(self):
        """Test the global register decorator function."""
        @register("global_test")
        class GlobalTestAnalyzer(TestAnalyzer):
            pass
        
        # Should be available in global registry
        global_registry = get_registry()
        analyzer_class = global_registry.get_analyzer("global_test")
        assert analyzer_class is not None
        assert analyzer_class == GlobalTestAnalyzer
    
    def test_get_registry_returns_same_instance(self):
        """Test that get_registry returns the same instance."""
        registry1 = get_registry()
        registry2 = get_registry()
        assert registry1 is registry2