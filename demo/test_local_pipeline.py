#!/usr/bin/env python3
"""Local pipeline regression test - verifies core functionality without external dependencies."""

import json
import tempfile
from pathlib import Path

from geoexhibit.config import create_default_config, validate_config
from geoexhibit.pipeline import (
    create_example_features,
    run_geoexhibit_pipeline,
)


def test_local_pipeline():
    """Test the complete GeoExhibit pipeline with local output (no external deps)."""
    print("🚀 Testing GeoExhibit Local Pipeline")
    print("=" * 50)

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # 1. Create configuration
        print("📋 Creating configuration...")
        config_data = create_default_config()
        config_data["aws"]["s3_bucket"] = "demo-test-bucket"
        config_data["project"]["name"] = "geoexhibit-demo"
        config_data["project"]["collection_id"] = "demo_fires"

        config_file = temp_path / "config.json"
        with open(config_file, "w") as f:
            json.dump(config_data, f, indent=2)
        print(f"  ✅ Configuration created: {config_file}")

        # 2. Create features
        print("🗺️  Creating demo features...")
        features = create_example_features()
        features_file = temp_path / "features.json"
        with open(features_file, "w") as f:
            json.dump(features, f, indent=2)
        print(f"  ✅ Features created: {features_file}")
        print(f"  📊 Feature count: {len(features['features'])}")

        # 3. Test dry run
        print("🔍 Testing dry run...")
        config = validate_config(config_data)

        dry_result = run_geoexhibit_pipeline(
            config=config, features_file=features_file, local_out_dir=None, dry_run=True
        )
        print("  ✅ Dry run completed")
        print(
            f"  📊 Would create {dry_result['item_count']} items from {dry_result['feature_count']} features"
        )
        print(f"  🆔 Job ID: {dry_result['job_id']}")

        # 4. Test local execution
        print("💾 Testing local execution...")
        output_dir = temp_path / "output"

        local_result = run_geoexhibit_pipeline(
            config=config,
            features_file=features_file,
            local_out_dir=output_dir,
            dry_run=False,
        )

        print("  ✅ Local execution completed")
        print(f"  📊 Created {local_result['item_count']} items")
        print(f"  📁 Output directory: {output_dir}")
        print(f"  ✅ Verification: {local_result.get('verification_passed', False)}")

        # 5. Verify output structure
        print("🔍 Verifying output structure...")
        job_dir = output_dir / f"jobs/{local_result['job_id']}"

        # Check STAC files
        collection_file = job_dir / "stac/collection.json"
        assert collection_file.exists(), f"Collection file missing: {collection_file}"

        with open(collection_file) as f:
            collection = json.load(f)
            assert collection["type"] == "Collection"
            assert collection["id"] == "demo_fires"

        print(f"  ✅ Collection JSON: {collection_file}")

        # Check item files
        items_dir = job_dir / "stac/items"
        item_files = list(items_dir.glob("*.json"))
        assert (
            len(item_files) >= 3
        ), f"Expected at least 3 item files, found {len(item_files)}"

        primary_cog_count = 0
        for item_file in item_files:
            with open(item_file) as f:
                item = json.load(f)
                assert item["type"] == "Feature"

                # Check for primary COG asset
                primary_assets = [
                    asset
                    for asset in item["assets"].values()
                    if isinstance(asset.get("roles"), list)
                    and "primary" in asset["roles"]
                    and "data" in asset["roles"]
                ]

                if primary_assets:
                    primary_cog_count += 1
                    # Verify S3 URL format
                    assert primary_assets[0]["href"].startswith(
                        "s3://demo-test-bucket/"
                    )

        print(
            f"  ✅ {len(item_files)} STAC Items with {primary_cog_count} primary COG assets"
        )

        # Check assets directory
        assets_dir = job_dir / "assets"
        assert assets_dir.exists(), f"Assets directory missing: {assets_dir}"

        asset_files = list(assets_dir.glob("**/*.tif"))
        assert (
            len(asset_files) >= 3
        ), f"Expected at least 3 COG files, found {len(asset_files)}"

        print(f"  ✅ {len(asset_files)} COG asset files generated")

        # 6. Test web scaffold readiness
        print("🗺️  Checking web scaffold...")
        web_index = Path("web_scaffold/index.html")
        web_app = Path("web_scaffold/app.js")

        assert web_index.exists(), "Web scaffold index.html missing"
        assert web_app.exists(), "Web scaffold app.js missing"

        print("  ✅ Web scaffold files present")
        print("  💡 To view map: Open web_scaffold/index.html and configure paths")

        # Summary
        print("\n🎉 DEMO WORKFLOW COMPLETED SUCCESSFULLY!")
        print("=" * 50)
        print("📊 Results:")
        print(f"  • Job ID: {local_result['job_id']}")
        print(f"  • Items: {local_result['item_count']}")
        print(f"  • Features: {local_result['feature_count']}")
        print(f"  • COG Files: {len(asset_files)}")
        print(f"  • Output: {output_dir}")
        print(f"  • Collection: jobs/{local_result['job_id']}/stac/collection.json")

        return local_result


if __name__ == "__main__":
    test_local_pipeline()
