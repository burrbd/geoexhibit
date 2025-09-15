#!/usr/bin/env python3
"""
Simple test to verify the fix for issue #16 - Collection item links should have 
proper relative hrefs instead of null.
"""

import sys
import os
from datetime import datetime, timezone

# Add the project directory to the path so we can import geoexhibit
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import pystac
    from geoexhibit.analyzer import AssetSpec, AnalyzerOutput
    from geoexhibit.config import validate_config
    from geoexhibit.publish_plan import PublishItem, PublishPlan
    from geoexhibit.stac_writer import write_stac_catalog
    from geoexhibit.timespan import TimeSpan
except ImportError as e:
    print(f"ImportError: {e}")
    sys.exit(1)


def create_test_config():
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


def create_test_plan():
    """Create a test PublishPlan."""
    analyzer_output = AnalyzerOutput(
        primary_cog_asset=AssetSpec(key="analysis", href="/analysis.tif")
    )
    
    publish_item = PublishItem(
        item_id="item-456",
        feature={
            "type": "Feature",
            "properties": {"feature_id": "feat-123", "name": "Test Feature"},
            "geometry": {"type": "Point", "coordinates": [138.6, -34.9]},
        },
        timespan=TimeSpan(start=datetime(2023, 9, 15, tzinfo=timezone.utc)),
        analyzer_output=analyzer_output,
    )
    
    return PublishPlan(
        collection_id="test_collection",
        job_id="job-123",
        items=[publish_item],
        collection_metadata={
            "title": "Test Collection",
            "description": "Test description",
            "keywords": ["test"],
            "license": "proprietary",
        },
    )


def test_collection_item_links_fix():
    """Test that Collection item links have proper hrefs, not null (issue #16 fix)."""
    print("Testing fix for issue #16: Collection item links should not have null hrefs")
    
    plan = create_test_plan()
    config = create_test_config()
    
    # This should not raise validation errors with our fix
    result = write_stac_catalog(plan, config)
    collection = result["collection"]["object"]
    
    # Find item links in the collection
    item_links = [link for link in collection.links if link.rel == "item"]
    
    print(f"Found {len(item_links)} item link(s)")
    
    # Check that we have at least one item link
    assert len(item_links) >= 1, "Expected at least 1 item link"
    
    # Check each item link
    for i, item_link in enumerate(item_links):
        print(f"  Item link {i}: href='{item_link.href}'")
        
        # The core fix: href should not be null/None
        assert item_link.href is not None, f"Item link {i} href should not be null (this was the bug in issue #16)"
        
        # The href should be a string
        assert isinstance(item_link.href, str), f"Item link {i} href should be a string"
        
        # The href should contain "items/" (relative path format)
        assert "items/" in item_link.href, f"Item link {i} href should contain 'items/' for proper relative path"
    
    print("✅ SUCCESS: All item links have non-null hrefs")
    print("✅ Issue #16 has been fixed - Collection item links no longer have null hrefs")
    return True


if __name__ == "__main__":
    print("=" * 60)
    try:
        success = test_collection_item_links_fix()
        if success:
            print("=" * 60)
            print("🎉 ISSUE #16 FIX VERIFIED:")
            print("   STAC Collection item links now have proper hrefs instead of null")
            print("   Steel thread validation should now pass")
    except Exception as e:
        print("=" * 60)
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)