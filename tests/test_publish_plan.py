"""Tests for PublishPlan and PublishItem data structures."""

from datetime import datetime, timezone

from geoexhibit.analyzer import AssetSpec, AnalyzerOutput
from geoexhibit.publish_plan import PublishItem, PublishPlan
from geoexhibit.timespan import TimeSpan


def test_publish_item_creation():
    """Test PublishItem creation and property access."""
    feature = {
        "type": "Feature",
        "properties": {"feature_id": "feat-123", "name": "Test Feature"},
        "geometry": {"type": "Point", "coordinates": [0, 0]},
    }

    timespan = TimeSpan(start=datetime(2023, 9, 15, tzinfo=timezone.utc))

    analyzer_output = AnalyzerOutput(
        primary_cog_asset=AssetSpec(key="analysis", href="/analysis.tif"),
        extra_properties={"analysis_type": "test"},
    )

    item = PublishItem(
        item_id="item-456",
        feature=feature,
        timespan=timespan,
        analyzer_output=analyzer_output,
    )

    assert item.item_id == "item-456"
    assert item.geometry == {"type": "Point", "coordinates": [0, 0]}
    assert item.feature_id == "feat-123"

    combined_props = item.properties
    assert combined_props["name"] == "Test Feature"
    assert combined_props["analysis_type"] == "test"


def test_publish_item_feature_id_fallback():
    """Test PublishItem uses item_id when feature_id is missing."""
    feature = {
        "type": "Feature",
        "properties": {"name": "Test Feature"},
        "geometry": {"type": "Point", "coordinates": [0, 0]},
    }

    timespan = TimeSpan(start=datetime(2023, 9, 15, tzinfo=timezone.utc))
    analyzer_output = AnalyzerOutput(
        primary_cog_asset=AssetSpec(key="analysis", href="/analysis.tif")
    )

    item = PublishItem(
        item_id="item-456",
        feature=feature,
        timespan=timespan,
        analyzer_output=analyzer_output,
    )

    assert item.feature_id == "item-456"


def test_publish_plan_creation():
    """Test PublishPlan creation and basic properties."""
    items = [
        _create_test_item("item-1", "feat-1"),
        _create_test_item("item-2", "feat-2"),
    ]

    plan = PublishPlan(
        collection_id="test-collection",
        job_id="job-123",
        items=items,
        collection_metadata={"title": "Test Collection"},
        pmtiles_path="features.pmtiles",
    )

    assert plan.collection_id == "test-collection"
    assert plan.job_id == "job-123"
    assert plan.item_count == 2
    assert plan.feature_count == 2
    assert plan.pmtiles_path == "features.pmtiles"


def test_publish_plan_feature_count_with_duplicates():
    """Test feature count calculation when same feature appears multiple times."""
    items = [
        _create_test_item("item-1", "feat-1"),
        _create_test_item("item-2", "feat-1"),  # Same feature, different time
        _create_test_item("item-3", "feat-2"),
    ]

    plan = PublishPlan(
        collection_id="test-collection",
        job_id="job-123",
        items=items,
        collection_metadata={},
    )

    assert plan.item_count == 3
    assert plan.feature_count == 2  # Only 2 unique features


def test_publish_plan_time_range():
    """Test time range calculation."""
    item1 = _create_test_item_with_time(
        "item-1", datetime(2023, 9, 15, tzinfo=timezone.utc)
    )
    item2 = _create_test_item_with_time(
        "item-2", datetime(2023, 9, 20, tzinfo=timezone.utc)
    )

    plan = PublishPlan(
        collection_id="test-collection",
        job_id="job-123",
        items=[item1, item2],
        collection_metadata={},
    )

    start, end = plan.time_range
    assert start == datetime(2023, 9, 15, tzinfo=timezone.utc)
    assert end == datetime(2023, 9, 20, tzinfo=timezone.utc)


def test_publish_plan_time_range_empty():
    """Test time range fails on empty plan."""
    plan = PublishPlan(
        collection_id="test-collection",
        job_id="job-123",
        items=[],
        collection_metadata={},
    )

    try:
        plan.time_range
        assert False, "Should have raised ValueError for empty plan"
    except ValueError as e:
        assert "empty publish plan" in str(e)


def test_publish_plan_get_items_for_feature():
    """Test getting items for a specific feature."""
    items = [
        _create_test_item("item-1", "feat-1"),
        _create_test_item("item-2", "feat-1"),
        _create_test_item("item-3", "feat-2"),
    ]

    plan = PublishPlan(
        collection_id="test-collection",
        job_id="job-123",
        items=items,
        collection_metadata={},
    )

    feat1_items = plan.get_items_for_feature("feat-1")
    assert len(feat1_items) == 2
    assert feat1_items[0].item_id == "item-1"
    assert feat1_items[1].item_id == "item-2"

    feat2_items = plan.get_items_for_feature("feat-2")
    assert len(feat2_items) == 1
    assert feat2_items[0].item_id == "item-3"


def test_publish_plan_validation_success():
    """Test successful publish plan validation."""
    items = [_create_test_item("item-1", "feat-1")]

    plan = PublishPlan(
        collection_id="test-collection",
        job_id="job-123",
        items=items,
        collection_metadata={},
    )

    plan.validate()  # Should not raise


def test_publish_plan_validation_failures():
    """Test various publish plan validation failures."""
    # Empty items
    plan = PublishPlan(
        collection_id="test", job_id="job-123", items=[], collection_metadata={}
    )
    try:
        plan.validate()
        assert False, "Should have raised ValueError for empty items"
    except ValueError as e:
        assert "at least one item" in str(e)

    # Missing collection_id
    plan = PublishPlan(
        collection_id="",
        job_id="job-123",
        items=[_create_test_item("item-1", "feat-1")],
        collection_metadata={},
    )
    try:
        plan.validate()
        assert False, "Should have raised ValueError for missing collection_id"
    except ValueError as e:
        assert "collection_id" in str(e)

    # Duplicate item IDs
    items = [
        _create_test_item("item-1", "feat-1"),
        _create_test_item("item-1", "feat-2"),  # Same item_id
    ]
    plan = PublishPlan(
        collection_id="test", job_id="job-123", items=items, collection_metadata={}
    )
    try:
        plan.validate()
        assert False, "Should have raised ValueError for duplicate item_id"
    except ValueError as e:
        assert "Duplicate item_id" in str(e)


def _create_test_item(item_id: str, feature_id: str) -> PublishItem:
    """Create a test PublishItem with minimal valid data."""
    return _create_test_item_with_time(
        item_id, datetime(2023, 9, 15, tzinfo=timezone.utc), feature_id
    )


def _create_test_item_with_time(
    item_id: str, start_time: datetime, feature_id: str = "feat-123"
) -> PublishItem:
    """Create a test PublishItem with specific time."""
    feature = {
        "type": "Feature",
        "properties": {"feature_id": feature_id, "name": "Test Feature"},
        "geometry": {"type": "Point", "coordinates": [0, 0]},
    }

    timespan = TimeSpan(start=start_time)

    analyzer_output = AnalyzerOutput(
        primary_cog_asset=AssetSpec(key="analysis", href="/analysis.tif")
    )

    return PublishItem(
        item_id=item_id,
        feature=feature,
        timespan=timespan,
        analyzer_output=analyzer_output,
    )
