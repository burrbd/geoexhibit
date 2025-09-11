"""End-to-end integration tests for GeoExhibit pipeline."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from geoexhibit.cli import main
from geoexhibit.config import create_default_config, validate_config
from geoexhibit.demo_analyzer import create_demo_analyzer
from geoexhibit.orchestrator import create_publish_plan
from geoexhibit.pipeline import create_example_features, run_geoexhibit_pipeline
from click.testing import CliRunner


def test_end_to_end_local_pipeline():
    """Test complete pipeline execution with local output."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create configuration
        config_data = create_default_config()
        config_data["aws"]["s3_bucket"] = "test-bucket"
        config = validate_config(config_data)

        # Create features file
        features = create_example_features()
        features_file = temp_path / "features.json"
        with open(features_file, "w") as f:
            json.dump(features, f)

        # Create output directory
        output_dir = temp_path / "geoexhibit_output"

        # Run pipeline
        result = run_geoexhibit_pipeline(
            config=config,
            features_file=features_file,
            local_out_dir=output_dir,
            dry_run=False,
        )

        # Verify result structure
        assert "job_id" in result
        assert result["collection_id"] == "my_collection"
        assert result["item_count"] >= 3  # At least 3 features
        assert result["output_type"] == "local"

        # Verify output files exist
        job_dir = output_dir / f"jobs/{result['job_id']}"

        # Check STAC files
        collection_file = job_dir / "stac/collection.json"
        assert collection_file.exists()

        with open(collection_file) as f:
            collection_data = json.load(f)
            assert collection_data["type"] == "Collection"
            assert collection_data["id"] == "my_collection"

        # Check at least one item file
        items_dir = job_dir / "stac/items"
        assert items_dir.exists()
        item_files = list(items_dir.glob("*.json"))
        assert len(item_files) >= 1

        # Verify item structure
        with open(item_files[0]) as f:
            item_data = json.load(f)
            assert item_data["type"] == "Feature"

            # Check for primary COG asset
            primary_assets = [
                asset
                for asset in item_data["assets"].values()
                if isinstance(asset.get("roles"), list)
                and "primary" in asset["roles"]
                and "data" in asset["roles"]
            ]
            assert len(primary_assets) >= 1

            # Verify S3 URL format for primary asset
            primary_asset = primary_assets[0]
            assert primary_asset["href"].startswith("s3://test-bucket/")
            assert "jobs/" in primary_asset["href"]
            assert "/assets/" in primary_asset["href"]


@patch("geoexhibit.pipeline.generate_pmtiles_plan")
def test_orchestrator_integration(mock_pmtiles):
    """Test orchestrator creates valid publish plans."""
    mock_pmtiles.return_value = "/tmp/features.pmtiles"

    # Create test configuration
    config_data = create_default_config()
    config_data["aws"]["s3_bucket"] = "integration-test-bucket"
    config = validate_config(config_data)

    # Create features
    features = create_example_features()

    # Create analyzer
    with tempfile.TemporaryDirectory() as temp_dir:
        analyzer = create_demo_analyzer(Path(temp_dir))

        # Create publish plan
        plan = create_publish_plan(features, analyzer, config)

        # Verify plan structure
        assert plan.collection_id == "my_collection"
        assert plan.item_count == 3  # 3 features
        assert len(plan.job_id) > 0

        # Verify all items have required components
        for item in plan.items:
            assert len(item.item_id) > 0
            assert item.geometry is not None
            assert item.analyzer_output.primary_cog_asset is not None

            # Check primary asset has correct properties
            primary_asset = item.analyzer_output.primary_cog_asset
            assert primary_asset.key == "analysis"
            assert "data" in (primary_asset.roles or [])

        # Verify plan validation passes
        plan.validate()  # Should not raise


def test_cli_integration():
    """Test CLI integration with local output."""
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create config file
        config_data = create_default_config()
        config_data["aws"]["s3_bucket"] = "cli-test-bucket"
        config_file = temp_path / "config.json"

        with open(config_file, "w") as f:
            json.dump(config_data, f)

        # Create features file
        features_file = temp_path / "features.json"
        with open(features_file, "w") as f:
            json.dump(create_example_features(), f)

        # Create output directory
        output_dir = temp_path / "output"

        # Change to temp directory so CLI can find features.json
        original_cwd = Path.cwd()
        import os

        os.chdir(temp_dir)

        try:
            # Test dry run
            result = runner.invoke(
                main,
                ["run", str(config_file), "--local-out", str(output_dir), "--dry-run"],
            )

            assert result.exit_code == 0
            assert "DRY RUN MODE" in result.output
            assert "cli-test-bucket" in result.output

        finally:
            os.chdir(original_cwd)


def test_config_validation_integration():
    """Test configuration validation with various scenarios."""
    # Valid configuration
    valid_config = create_default_config()
    config = validate_config(valid_config)
    assert config.s3_bucket == "your-bucket-name"
    assert config.collection_id == "my_collection"

    # Test time provider configuration
    assert config.time_config["mode"] == "declarative"
    assert config.time_config["extractor"] == "attribute_date"

    # Test extensions
    assert "proj" in config.use_extensions
    assert "raster" in config.use_extensions
    assert "processing" in config.use_extensions


def test_stac_href_enforcement():
    """Test that STAC HREF rules are properly enforced."""
    from geoexhibit.layout import CanonicalLayout
    from geoexhibit.stac_writer import HrefResolver

    config_data = create_default_config()
    config_data["aws"]["s3_bucket"] = "href-test-bucket"
    config = validate_config(config_data)

    layout = CanonicalLayout("test-job-123")
    resolver = HrefResolver(config, layout)

    # Test COG asset HREF (should be S3 URL)
    cog_href = resolver.resolve_cog_asset_href("item-456", "analysis.tif")
    assert cog_href.startswith("s3://href-test-bucket/")
    assert "jobs/test-job-123/assets/item-456/analysis.tif" in cog_href

    # Test thumbnail HREF (should be relative)
    thumb_href = resolver.resolve_thumbnail_href("item-456", "preview.png")
    assert thumb_href == "../thumbs/item-456/preview.png"
    assert not thumb_href.startswith("s3://")

    # Test PMTiles HREF (should be relative)
    pmtiles_href = resolver.resolve_pmtiles_href()
    assert pmtiles_href == "../pmtiles/features.pmtiles"
    assert not pmtiles_href.startswith("s3://")


def test_time_provider_integration():
    """Test time provider integration with different configurations."""
    from geoexhibit.declarative_time import DeclarativeTimeProvider

    # Test attribute_date extractor
    config = {
        "extractor": "attribute_date",
        "field": "properties.fire_date",
        "format": "auto",
        "tz": "UTC",
    }

    provider = DeclarativeTimeProvider(config)

    feature = {
        "type": "Feature",
        "properties": {"fire_date": "2023-09-15"},
        "geometry": {"type": "Point", "coordinates": [0, 0]},
    }

    spans = list(provider.for_feature(feature))
    assert len(spans) == 1
    assert spans[0].start.year == 2023
    assert spans[0].start.month == 9
    assert spans[0].start.day == 15


def test_analyzer_cog_generation():
    """Test that DemoAnalyzer generates valid COGs."""
    with tempfile.TemporaryDirectory() as temp_dir:
        analyzer = create_demo_analyzer(Path(temp_dir))

        feature = {
            "type": "Feature",
            "properties": {"feature_id": "integration-test"},
            "geometry": {"type": "Point", "coordinates": [138.6, -34.9]},
        }

        from geoexhibit.timespan import TimeSpan
        from datetime import datetime, timezone

        timespan = TimeSpan(start=datetime(2023, 9, 15, tzinfo=timezone.utc))

        result = analyzer.analyze(feature, timespan)

        # Verify analyzer output structure
        assert result.primary_cog_asset.key == "analysis"
        assert "data" in result.primary_cog_asset.roles

        # Verify COG file was created
        cog_path = Path(result.primary_cog_asset.href)
        assert cog_path.exists()
        assert cog_path.suffix == ".tif"

        # Check extra properties
        assert result.extra_properties["geoexhibit:analyzer"] == "demo_analyzer"
        assert result.extra_properties["geoexhibit:synthetic"] is True
