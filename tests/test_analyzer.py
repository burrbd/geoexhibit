"""Tests for Analyzer interface and related classes."""

from datetime import datetime, timezone
from typing import Dict, Any

from geoexhibit.analyzer import AssetSpec, AnalyzerOutput, Analyzer
from geoexhibit.timespan import TimeSpan


def test_asset_spec_creation():
    """Test AssetSpec data class creation."""
    asset = AssetSpec(
        key="test-asset",
        href="/path/to/asset.tif",
        title="Test Asset",
        media_type="image/tiff",
        roles=["data"],
    )

    assert asset.key == "test-asset"
    assert asset.href == "/path/to/asset.tif"
    assert asset.title == "Test Asset"
    assert asset.media_type == "image/tiff"
    assert asset.roles == ["data"]


def test_analyzer_output_creation():
    """Test AnalyzerOutput data class creation."""
    primary_asset = AssetSpec(key="primary", href="/primary.tif")
    additional_asset = AssetSpec(
        key="thumbnail", href="/thumb.png", roles=["thumbnail"]
    )

    output = AnalyzerOutput(
        primary_cog_asset=primary_asset,
        additional_assets=[additional_asset],
        extra_properties={"custom": "value"},
    )

    assert output.primary_cog_asset == primary_asset
    assert output.additional_assets == [additional_asset]
    assert output.extra_properties == {"custom": "value"}


def test_analyzer_output_all_assets():
    """Test AnalyzerOutput.all_assets property."""
    primary_asset = AssetSpec(key="primary", href="/primary.tif")
    additional_assets = [
        AssetSpec(key="thumbnail", href="/thumb.png"),
        AssetSpec(key="metadata", href="/meta.json"),
    ]

    output = AnalyzerOutput(
        primary_cog_asset=primary_asset, additional_assets=additional_assets
    )

    all_assets = output.all_assets
    assert len(all_assets) == 3
    assert all_assets[0] == primary_asset
    assert all_assets[1] == additional_assets[0]
    assert all_assets[2] == additional_assets[1]


class MockAnalyzer(Analyzer):
    """Mock analyzer for testing."""

    @property
    def name(self) -> str:
        return "mock-analyzer"

    def analyze(self, feature: Dict[str, Any], timespan: TimeSpan) -> AnalyzerOutput:
        return AnalyzerOutput(
            primary_cog_asset=AssetSpec(
                key="mock-cog", href="/mock.tif", roles=["data"]
            )
        )


def test_analyzer_interface():
    """Test Analyzer interface implementation."""
    analyzer = MockAnalyzer()

    feature = {
        "type": "Feature",
        "properties": {"id": "test"},
        "geometry": {"type": "Point", "coordinates": [0, 0]},
    }

    timespan = TimeSpan(start=datetime(2023, 1, 1, tzinfo=timezone.utc))

    result = analyzer.analyze(feature, timespan)

    assert isinstance(result, AnalyzerOutput)
    assert result.primary_cog_asset.key == "mock-cog"
    assert analyzer.name == "mock-analyzer"


def test_analyzer_abstract_methods():
    """Test that Analyzer abstract methods raise TypeError when not implemented."""
    try:
        from geoexhibit.analyzer import Analyzer

        # This should fail because analyze() is not implemented
        class IncompleteAnalyzer(Analyzer):
            @property
            def name(self) -> str:
                return "incomplete"

        IncompleteAnalyzer()
        assert False, "Should have raised TypeError for missing abstract method"
    except TypeError:
        pass  # Expected - abstract method not implemented

    try:
        # This should fail because name property is not implemented
        class AnotherIncompleteAnalyzer(Analyzer):
            def analyze(
                self, feature: Dict[str, Any], timespan: TimeSpan
            ) -> AnalyzerOutput:
                return AnalyzerOutput(
                    primary_cog_asset=AssetSpec(key="test", href="/test.tif")
                )

        AnotherIncompleteAnalyzer()
        assert False, "Should have raised TypeError for missing abstract property"
    except TypeError:
        pass  # Expected - abstract property not implemented
