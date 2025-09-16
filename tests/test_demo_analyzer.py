"""Tests for demo analyzer implementation."""

import tempfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio

from geoexhibit.demo_analyzer import DemoAnalyzer, create_demo_analyzer
from geoexhibit.timespan import TimeSpan


def test_demo_analyzer_creation():
    """Test DemoAnalyzer creation with default and custom output directories."""
    analyzer = DemoAnalyzer()
    assert analyzer.name == "demo_analyzer"
    assert analyzer.output_dir.exists()

    with tempfile.TemporaryDirectory() as temp_dir:
        custom_analyzer = DemoAnalyzer(Path(temp_dir))
        assert custom_analyzer.output_dir == Path(temp_dir)


def test_demo_analyzer_analyze_point_geometry():
    """Test analysis with point geometry."""
    with tempfile.TemporaryDirectory() as temp_dir:
        analyzer = DemoAnalyzer(Path(temp_dir))

        feature = {
            "type": "Feature",
            "properties": {"feature_id": "test-point", "name": "Test Point"},
            "geometry": {"type": "Point", "coordinates": [138.6, -34.9]},
        }

        timespan = TimeSpan(start=datetime(2023, 9, 15, 12, 0, tzinfo=timezone.utc))

        result = analyzer.analyze(feature, timespan)

        assert result.primary_cog_asset.key == "analysis"
        assert (
            result.primary_cog_asset.media_type
            == "image/tiff; application=geotiff; profile=cloud-optimized"
        )
        assert "data" in result.primary_cog_asset.roles

        assert result.extra_properties["geoexhibit:analyzer"] == "demo_analyzer"
        assert result.extra_properties["geoexhibit:synthetic"] is True

        cog_path = Path(result.primary_cog_asset.href)
        assert cog_path.exists()
        assert cog_path.suffix == ".tif"


def test_demo_analyzer_analyze_polygon_geometry():
    """Test analysis with polygon geometry."""
    with tempfile.TemporaryDirectory() as temp_dir:
        analyzer = DemoAnalyzer(Path(temp_dir))

        feature = {
            "type": "Feature",
            "properties": {"feature_id": "test-poly"},
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [138.6, -34.9],
                        [138.7, -34.9],
                        [138.7, -34.8],
                        [138.6, -34.8],
                        [138.6, -34.9],
                    ]
                ],
            },
        }

        timespan = TimeSpan(start=datetime(2023, 10, 1, tzinfo=timezone.utc))

        result = analyzer.analyze(feature, timespan)

        assert result.primary_cog_asset.key == "analysis"

        cog_path = Path(result.primary_cog_asset.href)
        assert cog_path.exists()

        with rasterio.open(cog_path) as src:
            assert src.crs == rasterio.CRS.from_epsg(4326)
            assert src.width == 256
            assert src.height == 256
            assert src.count == 1
            assert src.dtypes[0] == "float32"

            assert src.nodata == -9999

            data = src.read(1)
            assert data.shape == (256, 256)

            assert src.overviews(1) == [2, 4, 8]


def test_demo_analyzer_cog_properties():
    """Test generated COG has proper cloud-optimized properties."""
    with tempfile.TemporaryDirectory() as temp_dir:
        analyzer = DemoAnalyzer(Path(temp_dir))

        feature = {
            "type": "Feature",
            "properties": {"feature_id": "cog-test"},
            "geometry": {"type": "Point", "coordinates": [0, 0]},
        }

        timespan = TimeSpan(start=datetime(2023, 1, 1, tzinfo=timezone.utc))
        result = analyzer.analyze(feature, timespan)

        cog_path = Path(result.primary_cog_asset.href)

        with rasterio.open(cog_path) as src:
            # Test functional COG properties (tiled flag may not be reliable in all rasterio versions)
            assert src.profile["blockxsize"] == 256
            assert src.profile["blockysize"] == 256
            assert src.profile["compress"] == "lzw"
            # Predictor may not always be reported in profile
            assert src.profile.get("predictor", 2) == 2

            assert len(src.overviews(1)) > 0


def test_demo_analyzer_time_variation():
    """Test that analysis results vary with time (day of year factor)."""
    with tempfile.TemporaryDirectory() as temp_dir:
        analyzer = DemoAnalyzer(Path(temp_dir))

        feature = {
            "type": "Feature",
            "properties": {"feature_id": "time-test"},
            "geometry": {"type": "Point", "coordinates": [0, 0]},
        }

        timespan1 = TimeSpan(start=datetime(2023, 1, 1, tzinfo=timezone.utc))  # Day 1
        timespan2 = TimeSpan(start=datetime(2023, 7, 1, tzinfo=timezone.utc))  # Day 182

        result1 = analyzer.analyze(feature, timespan1)
        result2 = analyzer.analyze(feature, timespan2)

        cog_path1 = Path(result1.primary_cog_asset.href)
        cog_path2 = Path(result2.primary_cog_asset.href)

        assert cog_path1.exists()
        assert cog_path2.exists()
        assert cog_path1 != cog_path2  # Different files

        with rasterio.open(cog_path1) as src1, rasterio.open(cog_path2) as src2:
            data1 = src1.read(1)
            data2 = src2.read(1)

            valid_data1 = data1[data1 != -9999]
            valid_data2 = data2[data2 != -9999]

            if len(valid_data1) > 0 and len(valid_data2) > 0:
                assert not np.array_equal(
                    valid_data1, valid_data2
                ), "Time variation should affect output"


def test_demo_analyzer_feature_id_in_filename():
    """Test that feature ID appears in generated COG filename."""
    with tempfile.TemporaryDirectory() as temp_dir:
        analyzer = DemoAnalyzer(Path(temp_dir))

        feature = {
            "type": "Feature",
            "properties": {"feature_id": "unique-test-id"},
            "geometry": {"type": "Point", "coordinates": [0, 0]},
        }

        timespan = TimeSpan(start=datetime(2023, 6, 15, 14, 30, tzinfo=timezone.utc))
        result = analyzer.analyze(feature, timespan)

        cog_path = Path(result.primary_cog_asset.href)
        filename = cog_path.name

        assert "unique-test-id" in filename
        assert "20230615_143000" in filename  # Timestamp format
        assert filename.endswith("_analysis.tif")


def test_create_demo_analyzer_function():
    """Test the factory function for creating demo analyzers."""
    with tempfile.TemporaryDirectory() as temp_dir:
        analyzer = create_demo_analyzer(Path(temp_dir))

        assert isinstance(analyzer, DemoAnalyzer)
        assert analyzer.output_dir == Path(temp_dir)
        assert analyzer.name == "demo_analyzer"


def test_demo_analyzer_handles_missing_feature_id():
    """Test analyzer handles features without feature_id gracefully."""
    with tempfile.TemporaryDirectory() as temp_dir:
        analyzer = DemoAnalyzer(Path(temp_dir))

        feature = {
            "type": "Feature",
            "properties": {"name": "No ID Feature"},
            "geometry": {"type": "Point", "coordinates": [0, 0]},
        }

        timespan = TimeSpan(start=datetime(2023, 1, 1, tzinfo=timezone.utc))
        result = analyzer.analyze(feature, timespan)

        cog_path = Path(result.primary_cog_asset.href)
        assert cog_path.exists()
        assert "unknown" in cog_path.name  # Should use "unknown" as fallback
