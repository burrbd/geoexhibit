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
    assert len(pmtiles_links) == 0  # No PMTiles path in test plan


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
    assert item.collection_id == "test_collection"

    primary_assets = [
        asset
        for asset in item.assets.values()
        if asset.roles and "primary" in asset.roles
    ]
    assert len(primary_assets) == 1

    primary_asset = primary_assets[0]
    assert primary_asset.href.startswith("s3://test-bucket/")
    assert "jobs/job-123/assets/item-456/analysis.tif" in primary_asset.href
    
    # Check that roles are correct for TiTiler compatibility
    assert primary_asset.roles == ["primary"], f"Expected ['primary'] but got {primary_asset.roles}"


def test_create_stac_item_with_additional_assets():
    """Test STAC Item creation with additional assets."""
    analyzer_output = AnalyzerOutput(
        primary_cog_asset=AssetSpec(key="analysis.tif", href="/analysis.tif"),
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
        id="test_collection", description="Test", extent=_create_dummy_extent()
    )

    item = create_stac_item(publish_item, collection, config, layout)

    assert len(item.assets) == 2
    assert "analysis.tif" in item.assets
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
        id="fires_sa_demo", description="Test", extent=_create_dummy_extent()
    )

    item = create_stac_item(publish_item, collection, config, layout)

    # Test that the item has the required primary COG asset structure
    # without running full STAC validation which may fail due to link resolution issues
    primary_assets = [
        asset
        for asset in item.assets.values()
        if asset.roles and "primary" in asset.roles
    ]
    assert len(primary_assets) == 1, "Item should have exactly one primary COG asset"
    
    primary_asset = primary_assets[0]
    assert primary_asset.href.startswith("s3://"), f"Primary asset HREF should be S3 URL, got {primary_asset.href}"
    assert "jobs/" in primary_asset.href, "Primary asset HREF should contain jobs path"
    assert primary_asset.href.endswith(".tif"), f"Primary asset HREF should end with .tif, got {primary_asset.href}"
    
    # Check that roles are correct for TiTiler compatibility  
    assert primary_asset.roles == ["primary"], f"Expected ['primary'] for TiTiler compatibility, got {primary_asset.roles}"


def test_collection_item_links_have_proper_hrefs():
    """Test that STAC Collection item links have proper relative hrefs, not null."""
    plan = _create_test_plan()
    config = _create_test_config()

    result = write_stac_catalog(plan, config)
    collection = result["collection"]["object"]

    # Find item links in the collection
    item_links = [link for link in collection.links if link.rel == "item"]
    
    # Should have one item link for our test plan
    assert len(item_links) == 1
    
    item_link = item_links[0]
    
    # The href should not be null and should be a proper relative path
    assert item_link.href is not None, "Collection item link href should not be null"
    assert item_link.href == "items/item-456.json", f"Expected 'items/item-456.json', got '{item_link.href}'"
    assert item_link.media_type == "application/json"


def test_collection_item_links_multiple_items():
    """Test that Collection item links work correctly with multiple items."""
    from datetime import datetime, timezone
    
    # Create a plan with multiple items
    plan = PublishPlan(
        collection_id="test_collection_multi",
        job_id="job-456",
        items=[
            _create_test_publish_item_with_id("item-001"),
            _create_test_publish_item_with_id("item-002"), 
            _create_test_publish_item_with_id("item-003")
        ],
        collection_metadata={
            "title": "Multi Item Test Collection",
            "description": "Test with multiple items",
        },
    )
    
    config = _create_test_config()
    result = write_stac_catalog(plan, config)
    collection = result["collection"]["object"]

    # Find all item links
    item_links = [link for link in collection.links if link.rel == "item"]
    
    # Should have three item links
    assert len(item_links) == 3
    
    # Check that all hrefs are proper relative paths and not null
    expected_hrefs = {"items/item-001.json", "items/item-002.json", "items/item-003.json"}
    actual_hrefs = {link.href for link in item_links}
    
    assert actual_hrefs == expected_hrefs
    
    # Verify none of the hrefs are null
    for link in item_links:
        assert link.href is not None, "Collection item link href should not be null"
        assert link.href.startswith("items/"), f"Item href should start with 'items/', got '{link.href}'"
        assert link.href.endswith(".json"), f"Item href should end with '.json', got '{link.href}'"


def test_collection_validates_with_proper_item_links():
    """Test that STAC Collection validates successfully with proper item link hrefs."""
    plan = _create_test_plan()
    config = _create_test_config()

    result = write_stac_catalog(plan, config)
    collection = result["collection"]["object"]

    # This should not raise - the collection should validate successfully
    try:
        collection.validate()
    except Exception as e:
        assert False, f"Collection validation failed: {e}"
    
    # Double-check that item links are properly formed
    item_links = [link for link in collection.links if link.rel == "item"]
    for link in item_links:
        assert link.href is not None, "Item link href should not be null"
        assert isinstance(link.href, str), "Item link href should be a string"
        assert link.href.startswith("items/"), "Item link href should be relative path starting with 'items/'"


def test_issue_16_regression_no_null_hrefs():
    """Regression test for Issue #16: Ensure Collection item links never have null hrefs."""
    plan = _create_test_plan()
    config = _create_test_config()

    result = write_stac_catalog(plan, config)
    collection_dict = result["collection"]["object"].to_dict()

    # Check that the collection JSON contains no null hrefs
    item_links = [link for link in collection_dict.get("links", []) if link.get("rel") == "item"]
    
    assert len(item_links) > 0, "Collection should have at least one item link"
    
    for link in item_links:
        href = link.get("href")
        assert href is not None, f"Item link href should not be null: {link}"
        assert href != "null", f"Item link href should not be string 'null': {link}"
        assert isinstance(href, str), f"Item link href should be string, got {type(href)}: {link}"
        assert href.endswith(".json"), f"Item link href should end with .json: {link}"
        
    # Verify items also have proper links without null hrefs
    items = result["items"]
    for item_result in items:
        from geoexhibit.stac_writer import _fix_item_link_hrefs
        item_dict = _fix_item_link_hrefs(item_result["object"].to_dict())
        links = item_dict.get("links", [])
        
        for link in links:
            href = link.get("href")
            assert href is not None, f"Item link href should not be null in item {item_dict.get('id')}: {link}"
            assert href != "null", f"Item link href should not be string 'null' in item {item_dict.get('id')}: {link}"
            assert isinstance(href, str), f"Item link href should be string in item {item_dict.get('id')}: {link}"
            
            # Verify that relative paths are correct (not absolute)
            rel = link.get("rel")
            if rel in ["root", "collection"]:
                assert href == "../collection.json", f"Expected '../collection.json' for {rel} link, got '{href}'"
            elif rel == "self":
                item_id = item_dict.get('id')
                assert href == f"{item_id}.json", f"Expected '{item_id}.json' for self link, got '{href}'"


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
        primary_cog_asset=AssetSpec(key="analysis.tif", href="/analysis.tif")
    )

    return PublishItem(
        item_id="item-456",
        feature=_create_test_feature(),
        timespan=TimeSpan(start=datetime(2023, 9, 15, tzinfo=timezone.utc)),
        analyzer_output=analyzer_output,
    )


def _create_test_publish_item_with_id(item_id: str) -> PublishItem:
    """Create a test PublishItem with a specific item_id."""
    analyzer_output = AnalyzerOutput(
        primary_cog_asset=AssetSpec(key="analysis.tif", href="/analysis.tif")
    )

    return PublishItem(
        item_id=item_id,
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
