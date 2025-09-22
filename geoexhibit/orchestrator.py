"""Orchestrator for coordinating feature analysis and publish plan creation."""

import logging
from pathlib import Path
from typing import Dict, Any, Optional
from ulid import new as new_ulid

from .analyzer import Analyzer
from .config import GeoExhibitConfig
from .declarative_time import DeclarativeTimeProvider
from .plugin_registry import get_registry
from .publish_plan import PublishItem, PublishPlan
from .time_provider import TimeProvider, create_time_provider

logger = logging.getLogger(__name__)


def create_publish_plan(
    features: Dict[str, Any],
    analyzer: Analyzer,
    config: GeoExhibitConfig,
    time_provider: Optional[TimeProvider] = None,
) -> PublishPlan:
    """
    Create a complete publish plan from features, analyzer, and configuration.

    Args:
        features: GeoJSON FeatureCollection
        analyzer: Analyzer to process each feature/time combination
        config: GeoExhibit configuration
        time_provider: Optional time provider (will create from config if None)

    Returns:
        PublishPlan ready for publishing
    """
    if features.get("type") != "FeatureCollection":
        raise ValueError("Input must be a GeoJSON FeatureCollection")

    feature_list = features.get("features", [])
    if not feature_list:
        raise ValueError("FeatureCollection is empty")

    if time_provider is None:
        time_provider = _create_time_provider_from_config(config)

    job_id = str(new_ulid())
    items = []

    for feature in feature_list:
        _ensure_feature_has_id(feature, config.ids.get("prefix", ""))

        time_spans = list(time_provider.for_feature(feature))

        for timespan in time_spans:
            item_id = str(new_ulid())

            analyzer_output = analyzer.analyze(feature, timespan)

            item = PublishItem(
                item_id=item_id,
                feature=feature,
                timespan=timespan,
                analyzer_output=analyzer_output,
            )

            items.append(item)

    collection_metadata = _build_collection_metadata(config, features)

    plan = PublishPlan(
        collection_id=config.collection_id,
        job_id=job_id,
        items=items,
        collection_metadata=collection_metadata,
    )

    plan.validate()
    return plan


def _create_time_provider_from_config(config: GeoExhibitConfig) -> TimeProvider:
    """Create TimeProvider instance from configuration."""
    time_config = config.time_config

    if time_config["mode"] == "declarative":
        return DeclarativeTimeProvider(time_config)
    elif time_config["mode"] == "callable":
        provider_spec = time_config["provider"]
        return create_time_provider(provider_spec)
    else:
        raise ValueError(f"Unknown time provider mode: {time_config['mode']}")


def _ensure_feature_has_id(feature: Dict[str, Any], id_prefix: str = "") -> None:
    """Ensure feature has a feature_id property, generating one if missing."""
    props = feature.setdefault("properties", {})

    if "feature_id" not in props or not props["feature_id"]:
        feature_id = f"{id_prefix}{new_ulid()}" if id_prefix else str(new_ulid())
        props["feature_id"] = feature_id


def _build_collection_metadata(
    config: GeoExhibitConfig, features: Dict[str, Any]
) -> Dict[str, Any]:
    """Build collection metadata from configuration and feature collection."""
    feature_list = features.get("features", [])

    metadata = {
        "title": config.project["title"],
        "description": config.project["description"],
        "keywords": ["geospatial", "analysis", "raster"],
        "license": "proprietary",
    }

    if feature_list:
        metadata["feature_count"] = len(feature_list)

        geometry_types = set()
        for feature in feature_list:
            if "geometry" in feature and "type" in feature["geometry"]:
                geometry_types.add(feature["geometry"]["type"])

        if geometry_types:
            metadata["geometry_types"] = sorted(list(geometry_types))

    return metadata


def generate_pmtiles_plan(
    features: Dict[str, Any], config: GeoExhibitConfig, job_id: str
) -> str:
    """
    Generate PMTiles file path for the publish plan.

    Args:
        features: GeoJSON FeatureCollection
        config: GeoExhibit configuration
        job_id: Job ID for path generation

    Returns:
        Local path to generated PMTiles file
    """
    import tempfile
    from pathlib import Path

    temp_dir = Path(tempfile.mkdtemp())
    pmtiles_file = temp_dir / "features.pmtiles"

    try:
        _generate_pmtiles_from_features(features, pmtiles_file, config)
        return str(pmtiles_file)
    except Exception as e:
        raise RuntimeError(f"Failed to generate PMTiles: {e}")


def _generate_pmtiles_from_features(
    features: Dict[str, Any], output_path: Path, config: GeoExhibitConfig
) -> None:
    """Generate PMTiles file from features using tippecanoe."""
    import json
    import subprocess
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".geojson", delete=False) as f:
        json.dump(features, f)
        temp_geojson = f.name

    try:
        pmtiles_config = config.map.get("pmtiles", {})
        minzoom = pmtiles_config.get("minzoom", 5)
        maxzoom = pmtiles_config.get("maxzoom", 14)

        cmd = [
            "tippecanoe",
            "-o",
            str(output_path),
            "-z",
            str(maxzoom),
            "-Z",
            str(minzoom),
            "--force",
            "--no-tile-compression",
            "--drop-densest-as-needed",
            temp_geojson,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise RuntimeError(f"tippecanoe failed: {result.stderr}")

    finally:
        Path(temp_geojson).unlink(missing_ok=True)


def create_analyzer_from_config(config: GeoExhibitConfig) -> Analyzer:
    """Create an analyzer instance from configuration.
    
    Args:
        config: GeoExhibit configuration containing analyzer settings
        
    Returns:
        Analyzer instance
        
    Raises:
        ValueError: If analyzer cannot be created or not found
    """
    analyzer_config = config.analyzer_config
    analyzer_name = analyzer_config["name"]
    plugin_directories = analyzer_config.get("plugin_directories", ["analyzers/"])
    parameters = analyzer_config.get("parameters", {})
    
    registry = get_registry()
    
    # Auto-discover plugins from specified directories
    for plugin_dir in plugin_directories:
        plugin_path = Path(plugin_dir)
        if plugin_path.exists():
            logger.debug(f"Discovering plugins in {plugin_path}")
            registry.discover_plugins(plugin_path)
        else:
            logger.debug(f"Plugin directory {plugin_path} does not exist, skipping")
    
    # Handle built-in analyzers
    if analyzer_name == "demo_analyzer":
        # Import here to register the demo analyzer
        from .demo_analyzer import DemoAnalyzer
        return DemoAnalyzer(**parameters)
    
    # Try to create from registry
    try:
        return registry.create_analyzer(analyzer_name, **parameters)
    except ValueError as e:
        available_analyzers = list(registry.list_analyzers().keys())
        raise ValueError(
            f"Failed to create analyzer '{analyzer_name}': {e}. "
            f"Available analyzers: {available_analyzers}. "
            f"Make sure the plugin is installed in one of: {plugin_directories}"
        )


def create_publish_plan_from_config(
    features: Dict[str, Any],
    config: GeoExhibitConfig,
    time_provider: Optional[TimeProvider] = None,
) -> PublishPlan:
    """Create a complete publish plan from features and configuration.
    
    This is a convenience function that creates the analyzer from config
    and delegates to the main create_publish_plan function.
    
    Args:
        features: GeoJSON FeatureCollection
        config: GeoExhibit configuration (includes analyzer config)
        time_provider: Optional time provider (will create from config if None)
        
    Returns:
        PublishPlan ready for publishing
    """
    analyzer = create_analyzer_from_config(config)
    return create_publish_plan(features, analyzer, config, time_provider)
