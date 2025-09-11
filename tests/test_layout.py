"""Tests for CanonicalLayout path generation."""

from geoexhibit.layout import CanonicalLayout


def test_canonical_layout_basic_paths():
    """Test basic path generation for canonical layout."""
    layout = CanonicalLayout(job_id="test-job-123")

    assert layout.job_root == "jobs/test-job-123/"
    assert layout.stac_root == "jobs/test-job-123/stac/"
    assert layout.collection_path == "jobs/test-job-123/stac/collection.json"
    assert layout.items_root == "jobs/test-job-123/stac/items/"


def test_canonical_layout_item_paths():
    """Test item-specific path generation."""
    layout = CanonicalLayout(job_id="test-job-123")

    item_path = layout.item_path("item-456")
    assert item_path == "jobs/test-job-123/stac/items/item-456.json"


def test_canonical_layout_asset_paths():
    """Test asset path generation."""
    layout = CanonicalLayout(job_id="test-job-123")

    asset_path = layout.asset_path("item-456", "analysis.tif")
    assert asset_path == "jobs/test-job-123/assets/item-456/analysis.tif"

    thumb_path = layout.thumb_path("item-456", "preview.png")
    assert thumb_path == "jobs/test-job-123/thumbs/item-456/preview.png"


def test_canonical_layout_pmtiles_paths():
    """Test PMTiles path generation."""
    layout = CanonicalLayout(job_id="test-job-123")

    assert layout.pmtiles_root == "jobs/test-job-123/pmtiles/"
    assert layout.pmtiles_path == "jobs/test-job-123/pmtiles/features.pmtiles"


def test_canonical_layout_with_ulid():
    """Test layout with ULID-style job ID."""
    layout = CanonicalLayout(job_id="01ARZ3NDEKTSV4RRFFQ69G5FAV")

    assert layout.job_root == "jobs/01ARZ3NDEKTSV4RRFFQ69G5FAV/"
    assert (
        layout.collection_path == "jobs/01ARZ3NDEKTSV4RRFFQ69G5FAV/stac/collection.json"
    )

    item_path = layout.item_path("01ARZ3NDEKTSV4RRFFQ69G5FAX")
    assert (
        item_path
        == "jobs/01ARZ3NDEKTSV4RRFFQ69G5FAV/stac/items/01ARZ3NDEKTSV4RRFFQ69G5FAX.json"
    )
