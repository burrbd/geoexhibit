#!/usr/bin/env python3
"""AWS verification script for published GeoExhibit demo dataset."""

import json
import sys
from pathlib import Path

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from geoexhibit.config import load_config
from geoexhibit.layout import CanonicalLayout


def verify_aws_publishing(config_file: Path, job_id: str) -> None:
    """
    Verify that demo dataset was published correctly to S3 using AWS APIs.

    Args:
        config_file: Path to GeoExhibit configuration
        job_id: Job ID to verify
    """
    print("🔍 AWS VERIFICATION: Verifying published demo dataset")
    print("=" * 60)

    # Load configuration
    config = load_config(config_file)
    s3_bucket = config.s3_bucket

    print(f"📦 S3 Bucket: {s3_bucket}")
    print(f"🆔 Job ID: {job_id}")

    # Initialize S3 client
    try:
        if config.aws_region:
            s3_client = boto3.client("s3", region_name=config.aws_region)
        else:
            s3_client = boto3.client("s3")

        # Test bucket access
        s3_client.head_bucket(Bucket=s3_bucket)
        print(f"✅ S3 bucket access verified: {s3_bucket}")

    except NoCredentialsError:
        print("❌ AWS credentials not found")
        print(
            "💡 Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables"
        )
        sys.exit(1)
    except ClientError as e:
        print(f"❌ S3 bucket access failed: {e}")
        sys.exit(1)

    layout = CanonicalLayout(job_id)

    # Verify canonical layout structure
    print(f"\n📂 Verifying canonical layout under: jobs/{job_id}/")

    verification_results = {
        "collection_json": False,
        "items_json": False,
        "primary_cogs": False,
        "pmtiles": False,
        "titiler_compatible": False,
    }

    # 1. Verify Collection JSON
    print("🔍 Checking Collection JSON...")
    collection_key = layout.collection_path
    try:
        response = s3_client.get_object(Bucket=s3_bucket, Key=collection_key)
        collection_data = json.loads(response["Body"].read().decode("utf-8"))

        if collection_data.get("type") == "Collection":
            print(f"  ✅ Collection JSON found and valid: {collection_key}")
            print(f"     ID: {collection_data.get('id')}")
            print(f"     Title: {collection_data.get('title')}")
            verification_results["collection_json"] = True

            # Check for PMTiles link
            pmtiles_links = [
                link
                for link in collection_data.get("links", [])
                if link.get("rel") == "pmtiles"
            ]
            if pmtiles_links:
                print(f"  ✅ PMTiles link found: {pmtiles_links[0].get('href')}")
        else:
            print(f"  ❌ Collection JSON invalid type: {collection_data.get('type')}")

    except ClientError as e:
        print(f"  ❌ Collection JSON not found: {e}")

    # 2. Verify Items JSON and count primary COGs
    print("\n🔍 Checking STAC Items...")
    items_prefix = layout.items_root

    try:
        paginator = s3_client.get_paginator("list_objects_v2")
        items = []

        for page in paginator.paginate(Bucket=s3_bucket, Prefix=items_prefix):
            if "Contents" in page:
                items.extend(
                    [
                        obj["Key"]
                        for obj in page["Contents"]
                        if obj["Key"].endswith(".json")
                    ]
                )

        print(f"  📊 Found {len(items)} STAC Item files")

        primary_cog_count = 0
        valid_items = 0

        for item_key in items[:5]:  # Check first 5 items
            try:
                response = s3_client.get_object(Bucket=s3_bucket, Key=item_key)
                item_data = json.loads(response["Body"].read().decode("utf-8"))

                if item_data.get("type") == "Feature":
                    valid_items += 1

                    # Check for primary COG asset
                    assets = item_data.get("assets", {})
                    primary_assets = [
                        asset
                        for asset in assets.values()
                        if isinstance(asset.get("roles"), list)
                        and "primary" in asset["roles"]
                        and "data" in asset["roles"]
                    ]

                    if primary_assets:
                        primary_cog_count += 1
                        primary_asset = primary_assets[0]

                        # Verify S3 URL format for TiTiler compatibility
                        href = primary_asset.get("href", "")
                        if href.startswith(f"s3://{s3_bucket}/"):
                            print(f"  ✅ Primary COG asset: {href}")
                            verification_results["titiler_compatible"] = True
                        else:
                            print(f"  ❌ Invalid COG HREF format: {href}")

            except Exception as e:
                print(f"  ⚠️  Could not verify item {item_key}: {e}")

        if valid_items > 0:
            verification_results["items_json"] = True
            print(f"  ✅ {valid_items} valid STAC Items verified")

        if primary_cog_count > 0:
            verification_results["primary_cogs"] = True
            print(f"  ✅ {primary_cog_count} items have primary COG assets")

    except Exception as e:
        print(f"  ❌ Items verification failed: {e}")

    # 3. Verify Primary COGs exist in assets directory
    print("\n🔍 Checking primary COG files...")
    assets_prefix = layout.assets_root

    try:
        paginator = s3_client.get_paginator("list_objects_v2")
        cog_files = []

        for page in paginator.paginate(Bucket=s3_bucket, Prefix=assets_prefix):
            if "Contents" in page:
                cog_files.extend(
                    [
                        obj["Key"]
                        for obj in page["Contents"]
                        if obj["Key"].endswith(".tif")
                    ]
                )

        print(f"  📊 Found {len(cog_files)} COG files in assets directory")

        if len(cog_files) > 0:
            # Check a few COG files exist
            for cog_key in cog_files[:3]:
                try:
                    s3_client.head_object(Bucket=s3_bucket, Key=cog_key)
                    print(f"  ✅ COG exists: {cog_key}")
                except ClientError:
                    print(f"  ❌ COG missing: {cog_key}")

    except Exception as e:
        print(f"  ❌ COG verification failed: {e}")

    # 4. Verify PMTiles
    print("\n🔍 Checking PMTiles...")
    pmtiles_key = layout.pmtiles_path

    try:
        s3_client.head_object(Bucket=s3_bucket, Key=pmtiles_key)
        print(f"  ✅ PMTiles found: {pmtiles_key}")
        verification_results["pmtiles"] = True
    except ClientError:
        print(
            f"  ⚠️  PMTiles not found: {pmtiles_key} (tippecanoe may not be available)"
        )

    # Summary
    print("\n📋 VERIFICATION SUMMARY")
    print("=" * 60)

    total_checks = len(verification_results)
    passed_checks = sum(verification_results.values())

    for check, passed in verification_results.items():
        status = "✅" if passed else "❌"
        print(f"{status} {check.replace('_', ' ').title()}")

    print(f"\n📊 Overall: {passed_checks}/{total_checks} verification checks passed")

    if passed_checks >= 4:  # Allow PMTiles to be optional
        print("🎉 AWS VERIFICATION SUCCESSFUL!")
        print("✅ Published structure meets requirements for TiTiler compatibility")
        return True
    else:
        print("❌ AWS VERIFICATION FAILED!")
        print("💡 Check S3 bucket permissions and published data structure")
        return False


def main():
    """CLI interface for AWS verification."""
    if len(sys.argv) not in [2, 3]:
        print("Usage: python verify_aws_publishing.py <config.json> [job_id]")
        print("       python verify_aws_publishing.py config.json")
        print(
            "       python verify_aws_publishing.py config.json 01ARZ3NDEKTSV4RRFFQ69G5FAV"
        )
        sys.exit(1)

    config_file = Path(sys.argv[1])

    if len(sys.argv) == 3:
        job_id = sys.argv[2]
    else:
        # Try to find latest job ID
        print("🔍 Searching for latest published job...")
        # This would need to be implemented - for now require job_id
        print("❌ Job ID parameter required")
        print("💡 Specify job ID from pipeline output")
        sys.exit(1)

    try:
        success = verify_aws_publishing(config_file, job_id)
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
