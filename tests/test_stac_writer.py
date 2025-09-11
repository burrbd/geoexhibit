"""Tests for STAC writing functionality."""

from datetime import datetime, timezone
from pathlib import Path

import pystac

from geoexhibit.analyzer import AssetSpec, AnalyzerOutput
from geoexhibit.config import GeoExhibitConfig, validate_config
from geoexhibit.layout import CanonicalLayout
from geoexhibit.publish_plan import PublishItem, PublishPlan
from geoexhibit.stac_writer import (
    HrefResolver,
    create_stac_collection,
    create_stac_item,
    write_stac_catalog,
)
from geoexhibit.timespan import TimeSpan


def test_href_resolver_cog_assets():
    """Test HrefResolver generates correct S3 URLs for COG assets."""
    config = _create_test_config()
    layout = CanonicalLayout("job-123")
    resolver = HrefResolver(config, layout)

    href = resolver.resolve_cog_asset_href("item-456", "analysis.tif")
    expected = "s3://test-bucket/jobs/job-123/assets/item-456/analysis.tif"
    assert href == expected


def test_href_resolver_thumbnails():
    """Test HrefResolver generates relative paths for thumbnails."""
    config = _create_test_config()
    layout = CanonicalLayout("job-123")
    resolver = HrefResolver(config, layout)

    href = resolver.resolve_thumbnail_href("item-456", "preview.png")
    assert href == "../thumbs/item-456/preview.png"


def test_href_resolver_pmtiles():
    """Test HrefResolver generates relative PMTiles path."""
    config = _create_test_config()
    layout = CanonicalLayout("job-123")
    resolver = HrefResolver(config, layout)

    href = resolver.resolve_pmtiles_href()
    assert href == "../pmtiles/features.pmtiles"


def test_create_stac_collection():
    """Test STAC Collection creation."""
    plan = _create_test_plan()
    config = _create_test_config()
    layout = CanonicalLayout(plan.job_id)

    collection = create_stac_collection(plan, config, layout)

    assert isinstance(collection, pystac.Collection)
    assert collection.id == "test_collection"
    assert collection.title == "Test Collection"

    assert collection.extent.temporal.intervals[0][0] == datetime(
        2023, 9, 15, tzinfo=timezone.utc
    )

    pmtiles_links = [link for link in collection.links if link.rel == "pmtiles"]
    assert len(pmtiles_links) == 1
    assert pmtiles_links[0].target == "../pmtiles/features.pmtiles"


def test_create_stac_item():
    """Test STAC Item creation with primary COG asset."""
    publish_item = _create_test_publish_item()

    config = _create_test_config()
    layout = CanonicalLayout("job-123")

    collection = pystac.Collection(
        id="test_collection", description="Test", extent=_create_dummy_extent()
    )

    item = create_stac_item(publish_item, collection, config, layout)

    assert isinstance(item, pystac.Item)
    assert item.id == "item-456"
    assert item.collection == "test_collection"

    primary_assets = [
        asset
        for asset in item.assets.values()
        if asset.roles and "primary" in asset.roles and "data" in asset.roles
    ]
    assert len(primary_assets) == 1

    primary_asset = primary_assets[0]
    assert primary_asset.href.startswith("s3://test-bucket/")
    assert "jobs/job-123/assets/item-456/analysis.tif" in primary_asset.href


def test_create_stac_item_with_additional_assets():
    """Test STAC Item creation with additional assets."""
    analyzer_output = AnalyzerOutput(
        primary_cog_asset=AssetSpec(key="analysis", href="/analysis.tif"),
        additional_assets=[
            AssetSpec(
                key="thumbnail.png",
                href="/thumb.png",
                roles=["thumbnail"],
                media_type="image/png",
            )
        ],
    )

    publish_item = PublishItem(
        item_id="item-456",
        feature=_create_test_feature(),
        timespan=TimeSpan(start=datetime(2023, 9, 15, tzinfo=timezone.utc)),
        analyzer_output=analyzer_output,
    )

    config = _create_test_config()
    layout = CanonicalLayout("job-123")
    collection = pystac.Collection(
        id="test", description="Test", extent=_create_dummy_extent()
    )

    item = create_stac_item(publish_item, collection, config, layout)

    assert len(item.assets) == 2
    assert "analysis" in item.assets
    assert "thumbnail.png" in item.assets

    thumb_asset = item.assets["thumbnail.png"]
    assert thumb_asset.href == "../thumbs/item-456/thumbnail.png"
    assert "thumbnail" in thumb_asset.roles


def test_write_stac_catalog_s3_mode():
    """Test writing STAC catalog in S3 mode (no output_dir)."""
    plan = _create_test_plan()
    config = _create_test_config()

    result = write_stac_catalog(plan, config)

    assert "collection" in result
    assert "items" in result
    assert "layout" in result

    assert result["collection"]["path"].startswith("jobs/")
    assert result["collection"]["path"].endswith("stac/collection.json")

    assert len(result["items"]) == 1
    item_path = result["items"][0]["path"]
    assert item_path.startswith("jobs/")
    assert item_path.endswith("stac/items/item-456.json")


def test_write_stac_catalog_local_mode():
    """Test writing STAC catalog in local mode (with output_dir)."""
    import tempfile

    plan = _create_test_plan()
    config = _create_test_config()

    with tempfile.TemporaryDirectory() as temp_dir:
        output_dir = Path(temp_dir)
        result = write_stac_catalog(plan, config, output_dir)

        collection_path = Path(result["collection"]["path"])
        assert collection_path.exists()

        item_path = Path(result["items"][0]["path"])
        assert item_path.exists()

        assert "jobs/" in str(collection_path)
        assert "/stac/" in str(collection_path)


def test_stac_item_validation():
    """Test STAC Item validation enforces primary COG asset requirements."""
    publish_item = _create_test_publish_item()
    config = _create_test_config()
    layout = CanonicalLayout("job-123")
    collection = pystac.Collection(
        id="test", description="Test", extent=_create_dummy_extent()
    )

    item = create_stac_item(publish_item, collection, config, layout)

    try:
        from geoexhibit.stac_writer import _validate_stac_item

        _validate_stac_item(item, config)  # Should not raise
    except ValueError:
        assert False, "Valid STAC item should pass validation"


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
        "stac": {"use_extensions": ["proj", "raster"], "geometry_in_item": True},
        "ids": {"strategy": "ulid"},
        "time": {
            "mode": "declarative",
            "extractor": "attribute_date",
            "field": "properties.date",
        },
    }
    return validate_config(config_data)


def _create_test_feature():
    """Create a test GeoJSON feature."""
    return {
        "type": "Feature",
        "properties": {"feature_id": "feat-123", "name": "Test Feature"},
        "geometry": {"type": "Point", "coordinates": [138.6, -34.9]},
    }


def _create_test_publish_item() -> PublishItem:
    """Create a test PublishItem."""
    analyzer_output = AnalyzerOutput(
        primary_cog_asset=AssetSpec(key="analysis", href="/analysis.tif")
    )

    return PublishItem(
        item_id="item-456",
        feature=_create_test_feature(),
        timespan=TimeSpan(start=datetime(2023, 9, 15, tzinfo=timezone.utc)),
        analyzer_output=analyzer_output,
    )


def _create_test_plan() -> PublishPlan:
    """Create a test PublishPlan."""
    return PublishPlan(
        collection_id="test_collection",
        job_id="job-123",
        items=[_create_test_publish_item()],
        collection_metadata={
            "title": "Test Collection",
            "description": "Test description",
            "keywords": ["test"],
            "license": "proprietary",
        },
    )


def _create_dummy_extent() -> pystac.Extent:
    """Create a dummy extent for test collections."""
    spatial = pystac.SpatialExtent([[0, 0, 1, 1]])
    temporal = pystac.TemporalExtent(
        [[datetime(2023, 1, 1, tzinfo=timezone.utc), None]]
    )
    return pystac.Extent(spatial=spatial, temporal=temporal)
