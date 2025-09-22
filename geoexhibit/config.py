"""Configuration management for GeoExhibit."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, Optional, List


@dataclass
class GeoExhibitConfig:
    """Main configuration for GeoExhibit."""

    project: Dict[str, Any]
    aws: Dict[str, Any]
    map: Dict[str, Any]
    stac: Dict[str, Any]
    ids: Dict[str, Any]
    time: Dict[str, Any]
    analyzer: Dict[str, Any]

    @property
    def s3_bucket(self) -> str:
        """Get S3 bucket name."""
        bucket = self.aws["s3_bucket"]
        assert isinstance(bucket, str)
        return bucket

    @property
    def aws_region(self) -> Optional[str]:
        """Get AWS region (optional)."""
        region = self.aws.get("region")
        return region if region is None or isinstance(region, str) else None

    @property
    def collection_id(self) -> str:
        """Get collection ID."""
        collection_id = self.project["collection_id"]
        assert isinstance(collection_id, str)
        return collection_id

    @property
    def project_name(self) -> str:
        """Get project name."""
        name = self.project["name"]
        assert isinstance(name, str)
        return name

    @property
    def use_extensions(self) -> List[str]:
        """Get STAC extensions to use."""
        extensions = self.stac.get("use_extensions", [])
        assert isinstance(extensions, list)
        return extensions

    @property
    def time_config(self) -> Dict[str, Any]:
        """Get time provider configuration."""
        return self.time

    @property
    def analyzer_config(self) -> Dict[str, Any]:
        """Get analyzer configuration."""
        return self.analyzer


def load_config(config_path: Path) -> GeoExhibitConfig:
    """Load and validate configuration from JSON file."""
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path, "r") as f:
        data = json.load(f)

    return validate_config(data)


def validate_config(data: Dict[str, Any]) -> GeoExhibitConfig:
    """Validate configuration data and return GeoExhibitConfig instance."""
    required_sections = ["project", "aws", "map", "stac", "ids", "time", "analyzer"]
    for section in required_sections:
        if section not in data:
            raise ValueError(f"Missing required configuration section: {section}")

    _validate_project_section(data["project"])
    _validate_aws_section(data["aws"])
    _validate_stac_section(data["stac"])
    _validate_ids_section(data["ids"])
    _validate_time_section(data["time"])
    _validate_analyzer_section(data["analyzer"])

    return GeoExhibitConfig(
        project=data["project"],
        aws=data["aws"],
        map=data["map"],
        stac=data["stac"],
        ids=data["ids"],
        time=data["time"],
        analyzer=data["analyzer"],
    )


def _validate_project_section(project: Dict[str, Any]) -> None:
    """Validate project configuration section."""
    required_fields = ["name", "collection_id", "title", "description"]
    for field in required_fields:
        if field not in project:
            raise ValueError(f"Missing required project field: {field}")


def _validate_aws_section(aws: Dict[str, Any]) -> None:
    """Validate AWS configuration section."""
    if "s3_bucket" not in aws:
        raise ValueError("Missing required AWS field: s3_bucket")


def _validate_stac_section(stac: Dict[str, Any]) -> None:
    """Validate STAC configuration section and set defaults."""
    if "use_extensions" not in stac:
        stac["use_extensions"] = ["proj", "raster", "processing"]
    if "geometry_in_item" not in stac:
        stac["geometry_in_item"] = True


def _validate_ids_section(ids: Dict[str, Any]) -> None:
    """Validate IDs configuration section and set defaults."""
    if "strategy" not in ids:
        ids["strategy"] = "ulid"


def _validate_time_section(time: Dict[str, Any]) -> None:
    """Validate time configuration section."""
    if "mode" not in time:
        raise ValueError("Missing required time field: mode")

    if time["mode"] not in ["declarative", "callable"]:
        raise ValueError("time.mode must be 'declarative' or 'callable'")

    if time["mode"] == "declarative":
        _validate_declarative_time_config(time)
    elif time["mode"] == "callable":
        _validate_callable_time_config(time)

    if "format" not in time:
        time["format"] = "auto"
    if "tz" not in time:
        time["tz"] = "UTC"


def _validate_declarative_time_config(time: Dict[str, Any]) -> None:
    """Validate declarative time configuration."""
    if "extractor" not in time:
        raise ValueError("Declarative time mode requires 'extractor' field")

    valid_extractors = [
        "attribute_date",
        "attribute_interval",
        "fixed_annual_dates",
        "from_epoch",
        "regex_from_string",
    ]
    if time["extractor"] not in valid_extractors:
        raise ValueError(
            f"Invalid extractor: {time['extractor']}. Must be one of: {valid_extractors}"
        )

    if time["extractor"] in [
        "attribute_date",
        "attribute_interval",
        "regex_from_string",
    ]:
        if "field" not in time:
            raise ValueError(
                f"Extractor {time['extractor']} requires 'field' specification"
            )


def _validate_callable_time_config(time: Dict[str, Any]) -> None:
    """Validate callable time configuration."""
    if "provider" not in time:
        raise ValueError("Callable time mode requires 'provider' field")


def _validate_analyzer_section(analyzer: Dict[str, Any]) -> None:
    """Validate analyzer configuration section."""
    if "name" not in analyzer:
        raise ValueError("Missing required analyzer field: name")
    
    # Set default plugin directories
    if "plugin_directories" not in analyzer:
        analyzer["plugin_directories"] = ["analyzers/"]
    
    # Ensure plugin_directories is a list
    if not isinstance(analyzer["plugin_directories"], list):
        raise ValueError("analyzer.plugin_directories must be a list")
    
    # Set default plugin parameters
    if "parameters" not in analyzer:
        analyzer["parameters"] = {}


def create_default_config() -> Dict[str, Any]:
    """Create a default configuration template."""
    return {
        "project": {
            "name": "my-geoexhibit-project",
            "collection_id": "my_collection",
            "title": "My GeoExhibit Collection",
            "description": "A collection of geospatial analyses",
        },
        "aws": {"s3_bucket": "your-bucket-name", "region": "ap-southeast-2"},
        "map": {
            "pmtiles": {
                "feature_id_property": "feature_id",
                "minzoom": 5,
                "maxzoom": 14,
            },
            "base_url": "",
        },
        "stac": {
            "use_extensions": ["proj", "raster", "processing"],
            "geometry_in_item": True,
        },
        "ids": {"strategy": "ulid", "prefix": ""},
        "time": {
            "mode": "declarative",
            "extractor": "attribute_date",
            "field": "properties.fire_date",
            "format": "auto",
            "tz": "UTC",
        },
        "analyzer": {
            "name": "demo_analyzer",
            "plugin_directories": ["analyzers/"],
            "parameters": {},
        },
    }
