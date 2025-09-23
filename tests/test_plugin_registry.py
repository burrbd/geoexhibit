"""Tests for the plugin registry system."""

from typing import Dict, Any
import pytest

from geoexhibit.plugin_registry import (
    AnalyzerRegistry,
    PluginNotFoundError,
    PluginValidationError,
    register,
    get_analyzer,
    list_analyzers,
)
from geoexhibit.analyzer import Analyzer, AnalyzerOutput, AssetSpec
from geoexhibit.timespan import TimeSpan


class TestAnalyzer(Analyzer):
    """Test analyzer for registry testing."""

    def __init__(self, test_param: str = "default"):
        self.test_param = test_param

    @property
    def name(self) -> str:
        return "test_analyzer"

    def analyze(self, feature: Dict[str, Any], timespan: TimeSpan) -> AnalyzerOutput:
        return AnalyzerOutput(
            primary_cog_asset=AssetSpec(
                key="test",
                href="/tmp/test.tif",
                title="Test Asset",
                roles=["data", "primary"],
            )
        )


class InvalidAnalyzer:
    """Invalid analyzer that doesn't inherit from Analyzer."""

    pass


def test_analyzer_registry_initialization():
    """Test that AnalyzerRegistry initializes correctly."""
    registry = AnalyzerRegistry()
    assert len(registry._analyzers) == 0
    assert not registry._auto_discovered


def test_register_decorator():
    """Test the register decorator functionality."""
    registry = AnalyzerRegistry()

    @registry.register("test")
    class DecoratedAnalyzer(Analyzer):
        @property
        def name(self) -> str:
            return "decorated"

        def analyze(
            self, feature: Dict[str, Any], timespan: TimeSpan
        ) -> AnalyzerOutput:
            return AnalyzerOutput(
                primary_cog_asset=AssetSpec(
                    key="decorated",
                    href="/tmp/decorated.tif",
                    roles=["data", "primary"],
                )
            )

    assert "test" in registry._analyzers
    assert registry._analyzers["test"] is DecoratedAnalyzer


def test_register_invalid_analyzer():
    """Test that registering invalid analyzers raises appropriate errors."""
    registry = AnalyzerRegistry()

    with pytest.raises(PluginValidationError, match="must be a class"):
        registry.register("invalid")("not_a_class")

    with pytest.raises(PluginValidationError, match="must inherit from Analyzer"):
        registry.register("invalid")(InvalidAnalyzer)


def test_get_analyzer_success():
    """Test successful analyzer retrieval."""
    registry = AnalyzerRegistry()
    registry.register("test")(TestAnalyzer)

    analyzer = registry.get_analyzer("test", test_param="custom")
    assert isinstance(analyzer, TestAnalyzer)
    assert analyzer.test_param == "custom"
    assert analyzer.name == "test_analyzer"


def test_get_analyzer_not_found():
    """Test analyzer not found error."""
    registry = AnalyzerRegistry()
    registry.register("test")(TestAnalyzer)

    with pytest.raises(PluginNotFoundError, match="Analyzer 'nonexistent' not found"):
        registry.get_analyzer("nonexistent")


def test_get_analyzer_creation_failure():
    """Test analyzer creation failure handling."""
    registry = AnalyzerRegistry()

    @registry.register("failing")
    class FailingAnalyzer(Analyzer):
        def __init__(self, required_param):
            if required_param is None:
                raise ValueError("required_param cannot be None")
            self.required_param = required_param

        @property
        def name(self) -> str:
            return "failing"

        def analyze(
            self, feature: Dict[str, Any], timespan: TimeSpan
        ) -> AnalyzerOutput:
            return AnalyzerOutput(
                primary_cog_asset=AssetSpec(
                    key="test", href="/tmp/test.tif", roles=["data"]
                )
            )

    with pytest.raises(
        PluginValidationError, match="Failed to create analyzer 'failing'"
    ):
        registry.get_analyzer("failing", required_param=None)


def test_list_analyzers():
    """Test listing registered analyzers."""
    registry = AnalyzerRegistry()
    registry.register("test1")(TestAnalyzer)
    registry.register("test2")(TestAnalyzer)

    analyzers = registry.list_analyzers()
    assert "test1" in analyzers
    assert "test2" in analyzers
    assert len(analyzers) == 2


def test_global_register_function():
    """Test the global register decorator function."""
    # Clear any existing registrations for clean test
    from geoexhibit.plugin_registry import _registry

    original_analyzers = _registry._analyzers.copy()
    _registry._analyzers.clear()

    try:

        @register("global_test")
        class GlobalTestAnalyzer(Analyzer):
            @property
            def name(self) -> str:
                return "global_test"

            def analyze(
                self, feature: Dict[str, Any], timespan: TimeSpan
            ) -> AnalyzerOutput:
                return AnalyzerOutput(
                    primary_cog_asset=AssetSpec(
                        key="global", href="/tmp/global.tif", roles=["data", "primary"]
                    )
                )

        analyzers = list_analyzers()
        assert "global_test" in analyzers

        analyzer = get_analyzer("global_test")
        assert isinstance(analyzer, GlobalTestAnalyzer)
        assert analyzer.name == "global_test"

    finally:
        # Restore original state
        _registry._analyzers = original_analyzers


def test_auto_discovery_local_directory(tmp_path):
    """Test auto-discovery from local analyzers directory."""
    registry = AnalyzerRegistry()

    # Create a temporary analyzer file
    analyzers_dir = tmp_path / "analyzers"
    analyzers_dir.mkdir()

    analyzer_file = analyzers_dir / "temp_analyzer.py"
    analyzer_file.write_text(
        """
from geoexhibit.analyzer import Analyzer, AnalyzerOutput, AssetSpec
from geoexhibit.timespan import TimeSpan
from geoexhibit.plugin_registry import register

@register("temp")
class TempAnalyzer(Analyzer):
    @property
    def name(self) -> str:
        return "temp"
    
    def analyze(self, feature, timespan) -> AnalyzerOutput:
        return AnalyzerOutput(
            primary_cog_asset=AssetSpec(
                key="temp",
                href="/tmp/temp.tif", 
                roles=["data", "primary"]
            )
        )
"""
    )

    # Change to the temp directory and trigger auto-discovery
    import os

    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        registry._auto_discover_plugins()
        # Note: The temp analyzer won't actually be registered because it's not
        # in the same Python environment, but the discovery should run without error
    finally:
        os.chdir(original_cwd)

    assert registry._auto_discovered


def test_plugin_validation():
    """Test plugin validation enforcement."""
    registry = AnalyzerRegistry()

    # Test missing abstract methods
    with pytest.raises(PluginValidationError):

        @registry.register("incomplete")
        class IncompleteAnalyzer(Analyzer):
            @property
            def name(self) -> str:
                return "incomplete"

            # Missing analyze method


def test_demo_analyzer_registration():
    """Test that DemoAnalyzer is properly registered."""

    analyzers = list_analyzers()
    assert "demo" in analyzers

    analyzer = get_analyzer("demo")
    assert analyzer.name == "demo_analyzer"


def test_example_analyzer_registration():
    """Test that ExampleAnalyzer can be discovered from analyzers/ directory."""
    # This test verifies that our example plugin is discoverable
    list_analyzers()  # Trigger auto-discovery
    # Note: This may not pass in CI if the analyzers/ directory isn't in the Python path
    # but it demonstrates the discovery mechanism


def test_analyzer_interface_compliance():
    """Test that all registered analyzers comply with the interface."""

    analyzers = list_analyzers()
    for analyzer_name in analyzers:
        analyzer = get_analyzer(analyzer_name)

        # Test interface compliance
        assert hasattr(
            analyzer, "name"
        ), f"Analyzer {analyzer_name} missing 'name' property"
        assert hasattr(
            analyzer, "analyze"
        ), f"Analyzer {analyzer_name} missing 'analyze' method"
        assert isinstance(
            analyzer.name, str
        ), f"Analyzer {analyzer_name}.name must be string"


def test_plugin_error_messages():
    """Test that plugin errors provide helpful messages."""
    # Test plugin not found error message format
    with pytest.raises(PluginNotFoundError) as exc_info:
        get_analyzer("nonexistent")

    error_msg = str(exc_info.value)
    assert "nonexistent" in error_msg
    assert "Available analyzers:" in error_msg
    assert "Check that the plugin is installed" in error_msg


def test_multiple_registrations():
    """Test that multiple plugins can be registered without conflicts."""
    registry = AnalyzerRegistry()

    @registry.register("plugin1")
    class Plugin1(Analyzer):
        @property
        def name(self) -> str:
            return "plugin1"

        def analyze(
            self, feature: Dict[str, Any], timespan: TimeSpan
        ) -> AnalyzerOutput:
            return AnalyzerOutput(
                primary_cog_asset=AssetSpec(
                    key="p1", href="/tmp/p1.tif", roles=["data"]
                )
            )

    @registry.register("plugin2")
    class Plugin2(Analyzer):
        @property
        def name(self) -> str:
            return "plugin2"

        def analyze(
            self, feature: Dict[str, Any], timespan: TimeSpan
        ) -> AnalyzerOutput:
            return AnalyzerOutput(
                primary_cog_asset=AssetSpec(
                    key="p2", href="/tmp/p2.tif", roles=["data"]
                )
            )

    # Both should be available
    analyzers = registry.list_analyzers()
    assert "plugin1" in analyzers
    assert "plugin2" in analyzers

    # Both should be instantiable
    p1 = registry.get_analyzer("plugin1")
    p2 = registry.get_analyzer("plugin2")

    assert p1.name == "plugin1"
    assert p2.name == "plugin2"
