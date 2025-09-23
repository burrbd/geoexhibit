"""Tests for publisher functionality."""

import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

from geoexhibit.analyzer import AssetSpec, AnalyzerOutput
from geoexhibit.config import GeoExhibitConfig, validate_config
from geoexhibit.layout import CanonicalLayout
from geoexhibit.publish_plan import PublishItem, PublishPlan
from geoexhibit.publisher import LocalPublisher, S3Publisher, create_publisher
from geoexhibit.timespan import TimeSpan


def test_create_publisher_local():
    """Test creating LocalPublisher when local_out_dir is provided."""
    config = _create_test_config()

    with tempfile.TemporaryDirectory() as temp_dir:
        local_dir = Path(temp_dir)
        publisher = create_publisher(config, local_out_dir=local_dir)

        assert isinstance(publisher, LocalPublisher)
        assert publisher.output_dir == local_dir


@patch("geoexhibit.publisher.boto3")
def test_create_publisher_s3(mock_boto3):
    """Test creating S3Publisher when no local_out_dir is provided."""
    mock_client = MagicMock()
    mock_boto3.client.return_value = mock_client

    config = _create_test_config()
    publisher = create_publisher(config)

    assert isinstance(publisher, S3Publisher)
    assert publisher.s3_bucket == "test-bucket"


def test_local_publisher_initialization():
    """Test LocalPublisher initialization."""
    config = _create_test_config()

    with tempfile.TemporaryDirectory() as temp_dir:
        output_dir = Path(temp_dir) / "output"
        publisher = LocalPublisher(output_dir, config)

        assert publisher.output_dir == output_dir
        assert output_dir.exists()


def test_local_publisher_publish_plan():
    """Test LocalPublisher publishing a plan."""
    config = _create_test_config()

    with tempfile.TemporaryDirectory() as temp_dir:
        output_dir = Path(temp_dir) / "output"
        work_dir = Path(temp_dir) / "work"
        work_dir.mkdir()

        # Create a test asset file
        test_asset = work_dir / "test_cog.tif"
        test_asset.write_text("dummy cog content")

        plan = _create_test_plan(str(test_asset))

        publisher = LocalPublisher(output_dir, config)
        publisher.publish_plan(plan)

        # Verify files were created
        layout = CanonicalLayout(plan.job_id)

        collection_file = output_dir / layout.collection_path
        assert collection_file.exists()

        item_file = output_dir / layout.item_path(plan.items[0].item_id)
        assert item_file.exists()

        asset_file = output_dir / layout.asset_path(
            plan.items[0].item_id, "analysis.tif"
        )
        assert asset_file.exists()


def test_local_publisher_verification():
    """Test LocalPublisher verification functionality."""
    config = _create_test_config()

    with tempfile.TemporaryDirectory() as temp_dir:
        output_dir = Path(temp_dir) / "output"
        work_dir = Path(temp_dir) / "work"
        work_dir.mkdir()

        test_asset = work_dir / "test_cog.tif"
        test_asset.write_text("dummy cog content")

        plan = _create_test_plan(str(test_asset))

        publisher = LocalPublisher(output_dir, config)
        publisher.publish_plan(plan)

        # Verification should pass
        assert publisher.verify_publication(plan) is True

        # Remove a file and verify should fail
        layout = CanonicalLayout(plan.job_id)
        collection_file = output_dir / layout.collection_path
        collection_file.unlink()

        assert publisher.verify_publication(plan) is False


@patch("geoexhibit.publisher.boto3")
def test_s3_publisher_initialization(mock_boto3):
    """Test S3Publisher initialization with mocked boto3."""
    mock_client = MagicMock()
    mock_boto3.client.return_value = mock_client

    config = _create_test_config()
    publisher = S3Publisher(config)

    assert publisher.s3_bucket == "test-bucket"
    assert publisher.dry_run is False
    mock_client.head_bucket.assert_called_once_with(Bucket="test-bucket")


@patch("geoexhibit.publisher.boto3")
def test_s3_publisher_dry_run_mode(mock_boto3):
    """Test S3Publisher in dry run mode."""
    mock_client = MagicMock()
    mock_boto3.client.return_value = mock_client

    config = _create_test_config()
    publisher = S3Publisher(config, dry_run=True)

    assert publisher.dry_run is True
    # head_bucket should not be called in dry run mode
    mock_client.head_bucket.assert_not_called()


@patch("geoexhibit.publisher.boto3")
def test_s3_publisher_aws_region(mock_boto3):
    """Test S3Publisher uses AWS region from config."""
    mock_boto3.client.return_value = MagicMock()

    config = _create_test_config()
    config.aws["region"] = "us-west-2"

    S3Publisher(config, dry_run=True)

    mock_boto3.client.assert_called_once_with("s3", region_name="us-west-2")


@patch("geoexhibit.publisher.boto3")
def test_s3_publisher_missing_credentials(mock_boto3):
    """Test S3Publisher handles missing AWS credentials."""
    from botocore.exceptions import NoCredentialsError

    mock_boto3.client.side_effect = NoCredentialsError()

    config = _create_test_config()

    try:
        S3Publisher(config)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "AWS credentials not found" in str(e)


@patch("geoexhibit.publisher.boto3")
def test_s3_publisher_bucket_not_found(mock_boto3):
    """Test S3Publisher handles missing S3 bucket."""
    from botocore.exceptions import ClientError

    mock_client = MagicMock()
    mock_client.head_bucket.side_effect = ClientError(
        {"Error": {"Code": "404"}}, "HeadBucket"
    )
    mock_boto3.client.return_value = mock_client

    config = _create_test_config()

    try:
        S3Publisher(config)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "S3 bucket not found" in str(e)


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
        "stac": {"use_extensions": ["proj"]},
        "ids": {"strategy": "ulid"},
        "time": {
            "mode": "declarative",
            "extractor": "attribute_date",
            "field": "properties.date",
        },
    }
    return validate_config(config_data)


def _create_test_plan(asset_href: str = "/test.tif") -> PublishPlan:
    """Create a test PublishPlan."""
    analyzer_output = AnalyzerOutput(
        primary_cog_asset=AssetSpec(key="analysis", href=asset_href)
    )

    item = PublishItem(
        item_id="test-item-123",
        feature={
            "type": "Feature",
            "properties": {"feature_id": "feat-123"},
            "geometry": {"type": "Point", "coordinates": [0, 0]},
        },
        timespan=TimeSpan(start=datetime(2023, 9, 15, tzinfo=timezone.utc)),
        analyzer_output=analyzer_output,
    )

    return PublishPlan(
        collection_id="test_collection",
        job_id="test-job-456",
        items=[item],
        collection_metadata={"title": "Test Collection", "description": "Test"},
    )
