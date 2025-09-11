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

        if dry_run:
            click.echo("🔍 DRY RUN MODE - showing planned actions:")
            click.echo(f"  Project: {config.project_name}")
            click.echo(f"  Collection: {config.collection_id}")
            if local_out:
                click.echo(f"  Output: Local directory {local_out}")
            else:
                click.echo(f"  Output: S3 bucket {config.s3_bucket}")
            return

        if local_out:
            click.echo(f"📁 Using local output directory: {local_out}")
        else:
            click.echo(f"☁️  Publishing to S3 bucket: {config.s3_bucket}")

        click.echo("🚧 Full pipeline implementation in progress...")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@main.group()
def features() -> None:
    """Feature import and processing commands."""
    pass


@features.command()
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


if __name__ == "__main__":
    main()
