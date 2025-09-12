"""Main pipeline orchestration for GeoExhibit run command."""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from .config import GeoExhibitConfig
from .demo_analyzer import create_demo_analyzer
from .orchestrator import create_publish_plan, generate_pmtiles_plan
from .publisher import create_publisher

logger = logging.getLogger(__name__)


def run_geoexhibit_pipeline(
    config: GeoExhibitConfig,
    features_file: Path,
    local_out_dir: Optional[Path] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Run the complete GeoExhibit pipeline.

    Args:
        config: GeoExhibit configuration
        features_file: Path to input features (GeoJSON/NDJSON/GeoPackage/Shapefile)
        local_out_dir: Optional local output directory
        dry_run: If True, don't actually publish

    Returns:
        Dictionary with pipeline results and metadata
    """
    logger.info(f"Starting GeoExhibit pipeline: {config.project_name}")

    features = load_and_validate_features(features_file)
    logger.info(f"Loaded {len(features['features'])} features")

    analyzer = create_demo_analyzer()
    logger.info(f"Created analyzer: {analyzer.name}")

    plan = create_publish_plan(features, analyzer, config)
    logger.info(
        f"Created publish plan: {plan.item_count} items from {plan.feature_count} features"
    )

    pmtiles_path = None
    try:
        pmtiles_path = generate_pmtiles_plan(features, config, plan.job_id)
        plan.pmtiles_path = pmtiles_path
        logger.info(f"Generated PMTiles: {pmtiles_path}")
    except Exception as e:
        logger.warning(f"PMTiles generation failed (tippecanoe required): {e}")

    publisher = create_publisher(config, local_out_dir, dry_run)

    if not dry_run:
        publisher.publish_plan(plan)
        verification_passed = publisher.verify_publication(plan)

        if not verification_passed:
            raise RuntimeError("Publication verification failed")

        logger.info("✅ Pipeline completed successfully with verification")
    else:
        logger.info("✅ Pipeline completed successfully (dry run)")

    return {
        "job_id": plan.job_id,
        "collection_id": plan.collection_id,
        "item_count": plan.item_count,
        "feature_count": plan.feature_count,
        "pmtiles_generated": pmtiles_path is not None,
        "output_type": "local" if local_out_dir else "s3",
        "dry_run": dry_run,
        "verification_passed": not dry_run and verification_passed,
    }


def load_and_validate_features(features_file: Path) -> Dict[str, Any]:
    """Load and validate feature collection from file."""
    if not features_file.exists():
        raise FileNotFoundError(f"Features file not found: {features_file}")

    suffix = features_file.suffix.lower()

    if suffix in [".json", ".geojson"]:
        with open(features_file) as f:
            features = json.load(f)
    elif suffix in [".ndjson", ".jsonl"]:
        features = load_ndjson_features(features_file)
    else:
        raise ValueError(f"Unsupported file format: {suffix}")

    validate_feature_collection(features)
    ensure_feature_ids(features)

    assert isinstance(features, dict)
    return features


def load_ndjson_features(ndjson_file: Path) -> Dict[str, Any]:
    """Load NDJSON file and convert to FeatureCollection."""
    features = []
    with open(ndjson_file) as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                feature = json.loads(line)
                if feature.get("type") == "Feature":
                    features.append(feature)
                else:
                    logger.warning(f"Line {line_num}: Not a GeoJSON Feature, skipping")
            except json.JSONDecodeError as e:
                logger.warning(f"Line {line_num}: Invalid JSON, skipping: {e}")

    return {"type": "FeatureCollection", "features": features}


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
            feature["properties"] = {}


def ensure_feature_ids(features: Dict[str, Any]) -> None:
    """Ensure all features have a feature_id property using ULIDs."""
    from ulid import ULID

    for feature in features["features"]:
        props = feature.get("properties", {})
        if "feature_id" not in props or not props["feature_id"]:
            props["feature_id"] = str(ULID())
            feature["properties"] = props


def create_example_features() -> Dict[str, Any]:
    """Create example features for testing and demonstration."""
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "name": "Sample Fire Area A",
                    "fire_date": "2023-09-15",
                    "severity": "high",
                    "area_hectares": 1250.5,
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [138.6, -34.9],
                            [138.7, -34.9],
                            [138.7, -34.8],
                            [138.6, -34.8],
                            [138.6, -34.9],
                        ]
                    ],
                },
            },
            {
                "type": "Feature",
                "properties": {
                    "name": "Sample Fire Area B",
                    "fire_date": "2023-10-02",
                    "severity": "moderate",
                    "area_hectares": 890.2,
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [138.8, -34.95],
                            [138.9, -34.95],
                            [138.9, -34.85],
                            [138.8, -34.85],
                            [138.8, -34.95],
                        ]
                    ],
                },
            },
            {
                "type": "Feature",
                "properties": {
                    "name": "Sample Fire Point",
                    "fire_date": "2023-11-20",
                    "severity": "low",
                    "area_hectares": 430.8,
                },
                "geometry": {"type": "Point", "coordinates": [139.1, -34.7]},
            },
        ],
    }
