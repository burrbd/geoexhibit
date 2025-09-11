"""Tests for CLI functionality."""

import json
import tempfile
from pathlib import Path

from click.testing import CliRunner

from geoexhibit.cli import main
from geoexhibit.config import create_default_config


def test_cli_main_help():
    """Test main CLI help message."""
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])

    assert result.exit_code == 0
    assert "GeoExhibit: Publish static STAC metadata" in result.output
    assert "run" in result.output
    assert "features" in result.output
    assert "config" in result.output


def test_cli_run_command_help():
    """Test run command help."""
    runner = CliRunner()
    result = runner.invoke(main, ["run", "--help"])

    assert result.exit_code == 0
    assert "Run complete GeoExhibit pipeline" in result.output
    assert "--local-out" in result.output
    assert "--dry-run" in result.output


def test_cli_run_dry_run():
    """Test run command in dry-run mode."""
    runner = CliRunner()

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        config_data = create_default_config()
        config_data["aws"]["s3_bucket"] = "test-bucket"
        json.dump(config_data, f)
        config_path = Path(f.name)

    try:
        result = runner.invoke(main, ["run", str(config_path), "--dry-run"])

        assert result.exit_code == 0
        assert "DRY RUN MODE" in result.output
        assert (
            "test-bucket" in result.output or "my-geoexhibit-project" in result.output
        )

    finally:
        config_path.unlink()


def test_cli_run_local_output():
    """Test run command with local output option."""
    runner = CliRunner()

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        config_data = create_default_config()
        json.dump(config_data, f)
        config_path = Path(f.name)

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = runner.invoke(
                main, ["run", str(config_path), "--local-out", temp_dir, "--dry-run"]
            )

            assert result.exit_code == 0
            assert "Local directory" in result.output

    finally:
        config_path.unlink()


def test_cli_run_invalid_config():
    """Test run command with invalid configuration file."""
    runner = CliRunner()

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump({"invalid": "config"}, f)
        config_path = Path(f.name)

    try:
        result = runner.invoke(main, ["run", str(config_path)])

        assert result.exit_code == 1
        assert "Error:" in result.output

    finally:
        config_path.unlink()


def test_cli_config_create():
    """Test config creation command."""
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as temp_dir:
        output_path = Path(temp_dir) / "test_config.json"
        result = runner.invoke(main, ["config", "--create", "-o", str(output_path)])

        assert result.exit_code == 0
        assert "Created default configuration" in result.output
        assert output_path.exists()

        # Verify the created config is valid JSON
        with open(output_path) as f:
            config_data = json.load(f)

        assert "project" in config_data
        assert "aws" in config_data
        assert "time" in config_data


def test_cli_config_no_create_flag():
    """Test config command without --create flag."""
    runner = CliRunner()
    result = runner.invoke(main, ["config"])

    assert result.exit_code == 0
    assert "Use --create to generate default configuration" in result.output


def test_cli_validate_command_no_config():
    """Test validate command when no config file exists."""
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as temp_dir:
        # Change to temp directory where no config exists
        original_cwd = Path.cwd()
        import os

        os.chdir(temp_dir)

        try:
            result = runner.invoke(main, ["validate"])

            assert result.exit_code == 0
            assert "No configuration file found" in result.output
            assert "Run 'geoexhibit config --create'" in result.output

        finally:
            os.chdir(original_cwd)


def test_cli_validate_command_valid_config():
    """Test validate command with valid configuration."""
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as temp_dir:
        config_path = Path(temp_dir) / "config.json"
        config_data = create_default_config()
        config_data["aws"]["s3_bucket"] = "test-bucket"

        with open(config_path, "w") as f:
            json.dump(config_data, f)

        # Change to temp directory
        original_cwd = Path.cwd()
        import os

        os.chdir(temp_dir)

        try:
            result = runner.invoke(main, ["validate"])

            assert result.exit_code == 0
            assert "Configuration is valid" in result.output
            assert "test-bucket" in result.output

        finally:
            os.chdir(original_cwd)


def test_cli_features_import_help():
    """Test features import command help."""
    runner = CliRunner()
    result = runner.invoke(main, ["features", "import", "--help"])

    assert result.exit_code == 0
    assert "Import and normalize features" in result.output
    assert "GeoJSON, NDJSON, GeoPackage, Shapefile" in result.output


def test_cli_features_pmtiles_help():
    """Test features pmtiles command help."""
    runner = CliRunner()
    result = runner.invoke(main, ["features", "pmtiles", "--help"])

    assert result.exit_code == 0
    assert "Generate PMTiles from GeoJSON" in result.output
    assert "--minzoom" in result.output
    assert "--maxzoom" in result.output


def test_cli_verbose_flag():
    """Test verbose logging flag."""
    runner = CliRunner()
    result = runner.invoke(main, ["--verbose", "--help"])

    assert result.exit_code == 0
    assert "--verbose" in result.output
