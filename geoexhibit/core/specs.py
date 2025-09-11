"""Configuration specifications and validation for GeoExhibit."""

import json
from pathlib import Path
from typing import Dict, Any, List
from .interfaces import GeoExhibitConfig


def load_config(config_path: Path) -> GeoExhibitConfig:
    """Load and validate configuration from JSON file."""
    with open(config_path, 'r') as f:
        data = json.load(f)
    
    # Validate required sections
    required_sections = ["project", "aws", "map", "stac", "ids", "time"]
    for section in required_sections:
        if section not in data:
            raise ValueError(f"Missing required configuration section: {section}")
    
    # Validate project section
    project = data["project"]
    required_project_fields = ["name", "collection_id", "title", "description"]
    for field in required_project_fields:
        if field not in project:
            raise ValueError(f"Missing required project field: {field}")
    
    # Validate AWS section
    aws = data["aws"]
    if "s3_bucket" not in aws:
        raise ValueError("Missing required AWS field: s3_bucket")
    
    # Validate STAC section defaults
    stac = data["stac"]
    if "use_extensions" not in stac:
        stac["use_extensions"] = ["proj", "raster", "processing"]
    if "geometry_in_item" not in stac:
        stac["geometry_in_item"] = True
    
    # Validate IDs section defaults
    ids = data["ids"]
    if "strategy" not in ids:
        ids["strategy"] = "ulid"
    
    # Validate time section
    time = data["time"]
    if "mode" not in time:
        raise ValueError("Missing required time field: mode")
    
    if time["mode"] not in ["declarative", "callable"]:
        raise ValueError("time.mode must be 'declarative' or 'callable'")
    
    if time["mode"] == "declarative":
        if "extractor" not in time:
            raise ValueError("Declarative time mode requires 'extractor' field")
        
        valid_extractors = ["attribute_date", "attribute_interval", "fixed_annual_dates", "from_epoch", "regex_from_string"]
        if time["extractor"] not in valid_extractors:
            raise ValueError(f"Invalid extractor: {time['extractor']}. Must be one of: {valid_extractors}")
        
        if time["extractor"] in ["attribute_date", "attribute_interval", "regex_from_string"]:
            if "field" not in time:
                raise ValueError(f"Extractor {time['extractor']} requires 'field' specification")
    
    elif time["mode"] == "callable":
        if "provider" not in time:
            raise ValueError("Callable time mode requires 'provider' field")
    
    # Set defaults for time config
    if "format" not in time:
        time["format"] = "auto"
    if "tz" not in time:
        time["tz"] = "UTC"
    
    return GeoExhibitConfig(
        project=project,
        aws=aws,
        map=data["map"],
        stac=stac,
        ids=ids,
        time=time
    )


def create_default_config() -> Dict[str, Any]:
    """Create a default configuration template."""
    return {
        "project": {
            "name": "my-geoexhibit-project",
            "collection_id": "my_collection",
            "title": "My GeoExhibit Collection",
            "description": "A collection of geospatial analyses"
        },
        "aws": {
            "s3_bucket": "your-bucket-name",
            "region": "ap-southeast-2"
        },
        "map": {
            "pmtiles": {
                "feature_id_property": "feature_id",
                "minzoom": 5,
                "maxzoom": 14
            },
            "base_url": ""
        },
        "stac": {
            "use_extensions": ["proj", "raster", "processing"],
            "geometry_in_item": True
        },
        "ids": {
            "strategy": "ulid",
            "prefix": ""
        },
        "time": {
            "mode": "declarative",
            "extractor": "attribute_date",
            "field": "properties.date",
            "format": "auto",
            "tz": "UTC"
        }
    }


def validate_feature_collection(features: Dict[str, Any]) -> None:
    """Validate that a GeoJSON FeatureCollection is properly structured."""
    if "type" not in features or features["type"] != "FeatureCollection":
        raise ValueError("Input must be a GeoJSON FeatureCollection")
    
    if "features" not in features:
        raise ValueError("FeatureCollection must have features array")
    
    if not isinstance(features["features"], list):
        raise ValueError("Features must be a list")
    
    for i, feature in enumerate(features["features"]):
        if "type" not in feature or feature["type"] != "Feature":
            raise ValueError(f"Feature {i} must have type 'Feature'")
        
        if "geometry" not in feature or not feature["geometry"]:
            raise ValueError(f"Feature {i} must have a geometry")
        
        if "properties" not in feature:
            # Add empty properties if missing
            feature["properties"] = {}


def ensure_feature_ids(features: Dict[str, Any], id_prefix: str = "") -> None:
    """Ensure all features have a feature_id property using ULIDs."""
    from ulid import ULID
    
    for feature in features["features"]:
        props = feature.get("properties", {})
        if "feature_id" not in props or not props["feature_id"]:
            # Generate new ULID for feature_id
            feature_id = f"{id_prefix}{ULID()}" if id_prefix else str(ULID())
            props["feature_id"] = feature_id
            feature["properties"] = props