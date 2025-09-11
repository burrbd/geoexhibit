"""Command-line interface for GeoExhibit."""

import json
import logging
import sys
from pathlib import Path
from typing import Optional

import click

from .config import load_config


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
def main(verbose: bool) -> None:
    """GeoExhibit: Publish static STAC metadata and raster outputs to S3."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )


@main.command()
@click.argument("config_file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--local-out",
    type=click.Path(path_type=Path),
    help="Local output directory (default: publish to S3)",
)
@click.option(
    "--dry-run", is_flag=True, help="Show what would be done without executing"
)
def run(config_file: Path, local_out: Optional[Path], dry_run: bool) -> None:
    """
    Run complete GeoExhibit pipeline from configuration.

    Default behavior is to publish to S3. Use --local-out <dir> to output locally.
    """
    try:
        config = load_config(config_file)
        click.echo(f"✅ Loaded configuration from {config_file}")

        # Auto-discover features file
        features_file = _discover_features_file()
        if not features_file:
            click.echo(
                "❌ No features file found. Create features.json or features.geojson"
            )
            sys.exit(1)

        click.echo(f"📥 Using features file: {features_file}")

        if dry_run:
            click.echo("🔍 DRY RUN MODE - showing planned actions:")
            click.echo(f"  Project: {config.project_name}")
            click.echo(f"  Collection: {config.collection_id}")
            click.echo(f"  Features: {features_file}")
            if local_out:
                click.echo(f"  Output: Local directory {local_out}")
            else:
                click.echo(f"  Output: S3 bucket {config.s3_bucket}")

            # In dry-run mode, show what would be done without importing heavy dependencies
            click.echo("  📊 Would analyze features with DemoAnalyzer")
            click.echo("  🗺️  Would generate PMTiles (if tippecanoe available)")
            click.echo("  📝 Would create STAC Collection and Items")
            if local_out:
                click.echo(f"  💾 Would copy files to: {local_out}")
            else:
                click.echo(
                    f"  ☁️  Would upload to: s3://{config.s3_bucket}/jobs/<job_id>/"
                )
            return
        else:
            if local_out:
                click.echo(f"📁 Using local output directory: {local_out}")
            else:
                click.echo(f"☁️  Publishing to S3 bucket: {config.s3_bucket}")

        # Import pipeline only when actually needed (not in dry-run)
        try:
            from .pipeline import run_geoexhibit_pipeline
        except ImportError as e:
            click.echo(f"❌ Missing dependencies for pipeline execution: {e}")
            click.echo("💡 Install with: pip install rasterio numpy shapely")
            sys.exit(1)

        result = run_geoexhibit_pipeline(config, features_file, local_out, dry_run)

        # Display results
        click.echo("\n🎉 Pipeline completed successfully!")
        click.echo(f"  Job ID: {result['job_id']}")
        click.echo(f"  Collection: {result['collection_id']}")
        click.echo(f"  Items created: {result['item_count']}")
        click.echo(f"  Features processed: {result['feature_count']}")

        if result.get("pmtiles_generated"):
            click.echo("  ✅ PMTiles generated")
        else:
            click.echo("  ⚠️  PMTiles not generated (tippecanoe required)")

        if not dry_run and result.get("verification_passed"):
            click.echo("  ✅ Publication verified")

        if local_out:
            click.echo(f"  📁 Output location: {local_out}")
        else:
            click.echo(
                f"  ☁️  Published to: s3://{config.s3_bucket}/jobs/{result['job_id']}/"
            )
            click.echo(
                f"  🗺️  Collection URL: s3://{config.s3_bucket}/jobs/{result['job_id']}/stac/collection.json"
            )

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@main.group()
def features() -> None:
    """Feature import and processing commands."""
    pass


@features.command("import")
@click.argument("input_file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Output path for normalized GeoJSON",
)
@click.option("--id-prefix", default="", help="Prefix for generated feature IDs")
def import_features(input_file: Path, output: Optional[Path], id_prefix: str) -> None:
    """
    Import and normalize features from various formats.

    Supports: GeoJSON, NDJSON, GeoPackage, Shapefile
    Outputs normalized GeoJSON FeatureCollection in EPSG:4326.
    """
    try:
        click.echo(f"📥 Importing features from {input_file}")

        if not output:
            output = input_file.with_suffix(".geojson")

        click.echo(f"📤 Would write normalized features to {output}")
        click.echo("🚧 Feature import implementation in progress...")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@features.command()
@click.argument("input_file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--output", "-o", type=click.Path(path_type=Path), help="Output path for PMTiles"
)
@click.option("--minzoom", default=5, help="Minimum zoom level")
@click.option("--maxzoom", default=14, help="Maximum zoom level")
def pmtiles(
    input_file: Path, output: Optional[Path], minzoom: int, maxzoom: int
) -> None:
    """
    Generate PMTiles from GeoJSON features.

    Ensures feature_id is preserved in tile properties.
    """
    try:
        click.echo(f"🗺️  Generating PMTiles from {input_file}")

        if not output:
            output = input_file.with_suffix(".pmtiles")

        click.echo(f"📤 Would write PMTiles to {output}")
        click.echo(f"🔍 Zoom range: {minzoom}-{maxzoom}")
        click.echo("🚧 PMTiles generation implementation in progress...")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.option("--create", is_flag=True, help="Create default configuration template")
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    default="config.json",
    help="Output path",
)
def config(create: bool, output: Path) -> None:
    """
    Configuration management commands.

    Use --create to generate a default configuration template.
    """
    if create:
        from .config import create_default_config

        default_config = create_default_config()

        with open(output, "w") as f:
            json.dump(default_config, f, indent=2)

        click.echo(f"✅ Created default configuration: {output}")
        click.echo(f"📝 Edit {output} with your settings before running GeoExhibit")
    else:
        click.echo("Use --create to generate default configuration")


@main.command()
def validate() -> None:
    """Validate current project setup and configuration."""
    click.echo("🔍 Validating project setup...")

    config_files = ["config.json", "geoexhibit.json"]
    config_found = None

    for config_file in config_files:
        if Path(config_file).exists():
            config_found = config_file
            break

    if not config_found:
        click.echo("❌ No configuration file found")
        click.echo("💡 Run 'geoexhibit config --create' to generate one")
        return

    try:
        config = load_config(Path(config_found))
        click.echo(f"✅ Configuration is valid: {config_found}")
        click.echo(f"  Project: {config.project_name}")
        click.echo(f"  Collection: {config.collection_id}")
        click.echo(f"  S3 Bucket: {config.s3_bucket}")

    except Exception as e:
        click.echo(f"❌ Configuration validation failed: {e}", err=True)
        sys.exit(1)


def _discover_features_file() -> Optional[Path]:
    """Auto-discover features file in common locations."""
    common_names = [
        "features.json",
        "features.geojson",
        "data.json",
        "data.geojson",
        "input.json",
        "input.geojson",
    ]

    for name in common_names:
        path = Path(name)
        if path.exists():
            return path

    return None


if __name__ == "__main__":
    main()
