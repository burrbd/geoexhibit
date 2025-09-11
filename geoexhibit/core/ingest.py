"""Feature ingestion and normalization for GeoExhibit."""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
import geopandas as gpd
from shapely.validation import make_valid
from shapely.geometry import shape
from .specs import validate_feature_collection, ensure_feature_ids

logger = logging.getLogger(__name__)


def ingest_features(input_path: Path, id_prefix: str = "") -> Dict[str, Any]:
    """
    Ingest features from various formats and normalize to GeoJSON FeatureCollection.
    
    Supports:
    - GeoJSON (.json, .geojson)
    - NDJSON (.ndjson, .jsonl)
    - GeoPackage (.gpkg)
    - Shapefile (.shp)
    
    Args:
        input_path: Path to the input file
        id_prefix: Optional prefix for generated feature IDs
        
    Returns:
        GeoJSON FeatureCollection in EPSG:4326
        
    Raises:
        ValueError: If input format is unsupported or data is invalid
        FileNotFoundError: If input file doesn't exist
    """
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")
    
    suffix = input_path.suffix.lower()
    
    try:
        if suffix in ['.json', '.geojson']:
            features = _read_geojson(input_path)
        elif suffix in ['.ndjson', '.jsonl']:
            features = _read_ndjson(input_path)
        elif suffix == '.gpkg':
            features = _read_geopackage(input_path)
        elif suffix == '.shp':
            features = _read_shapefile(input_path)
        else:
            raise ValueError(f"Unsupported file format: {suffix}")
        
        # Validate structure
        validate_feature_collection(features)
        
        # Validate and fix geometries
        valid_features, invalid_count = _validate_geometries(features)
        
        if invalid_count > 0:
            logger.warning(f"Fixed {invalid_count} invalid geometries")
        
        # Ensure all features have feature_id
        ensure_feature_ids(valid_features, id_prefix)
        
        # Ensure we're in EPSG:4326
        features_4326 = _ensure_epsg_4326(valid_features)
        
        logger.info(f"Successfully ingested {len(features_4326['features'])} features")
        
        return features_4326
        
    except Exception as e:
        raise ValueError(f"Failed to ingest features from {input_path}: {str(e)}")


def _read_geojson(path: Path) -> Dict[str, Any]:
    """Read GeoJSON file."""
    with open(path, 'r') as f:
        return json.load(f)


def _read_ndjson(path: Path) -> Dict[str, Any]:
    """Read NDJSON file and convert to FeatureCollection."""
    features = []
    with open(path, 'r') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                feature = json.loads(line)
                if feature.get('type') == 'Feature':
                    features.append(feature)
                else:
                    logger.warning(f"Line {line_num}: Not a GeoJSON Feature, skipping")
            except json.JSONDecodeError as e:
                logger.warning(f"Line {line_num}: Invalid JSON, skipping: {e}")
    
    return {
        "type": "FeatureCollection",
        "features": features
    }


def _read_geopackage(path: Path) -> Dict[str, Any]:
    """Read GeoPackage and convert to GeoJSON FeatureCollection."""
    gdf = gpd.read_file(path)
    return _geodataframe_to_geojson(gdf)


def _read_shapefile(path: Path) -> Dict[str, Any]:
    """Read Shapefile and convert to GeoJSON FeatureCollection."""
    gdf = gpd.read_file(path)
    return _geodataframe_to_geojson(gdf)


def _geodataframe_to_geojson(gdf: gpd.GeoDataFrame) -> Dict[str, Any]:
    """Convert GeoDataFrame to GeoJSON FeatureCollection."""
    # Convert to EPSG:4326 if needed
    if gdf.crs and gdf.crs != 'EPSG:4326':
        gdf = gdf.to_crs('EPSG:4326')
    
    # Convert to GeoJSON
    geojson_str = gdf.to_json()
    return json.loads(geojson_str)


def _validate_geometries(features: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    """
    Validate and fix invalid geometries.
    
    Returns:
        Tuple of (fixed_features, invalid_count)
    """
    invalid_count = 0
    fixed_features = []
    
    for i, feature in enumerate(features["features"]):
        try:
            # Convert to Shapely geometry
            geom = shape(feature["geometry"])
            
            # Check if valid
            if not geom.is_valid:
                # Try to fix the geometry
                fixed_geom = make_valid(geom)
                if fixed_geom.is_valid:
                    # Convert back to GeoJSON
                    feature["geometry"] = json.loads(gpd.GeoSeries([fixed_geom]).to_json())["features"][0]["geometry"]
                    invalid_count += 1
                    logger.debug(f"Fixed invalid geometry for feature {i}")
                else:
                    logger.error(f"Could not fix invalid geometry for feature {i}, skipping")
                    continue
            
            fixed_features.append(feature)
            
        except Exception as e:
            logger.error(f"Error processing geometry for feature {i}: {e}, skipping")
            continue
    
    return {
        "type": "FeatureCollection",
        "features": fixed_features
    }, invalid_count


def _ensure_epsg_4326(features: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure features are in EPSG:4326."""
    # For now, assume input is already in the correct CRS or has been converted
    # In a more complete implementation, we'd check and convert CRS here
    return features


def generate_pmtiles_source(features: Dict[str, Any], output_path: Path, 
                          minzoom: int = 5, maxzoom: int = 14) -> None:
    """
    Generate PMTiles from feature collection.
    
    Args:
        features: GeoJSON FeatureCollection
        output_path: Path for output PMTiles file
        minzoom: Minimum zoom level
        maxzoom: Maximum zoom level
    """
    # Create a temporary GeoJSON file for tippecanoe
    temp_geojson = output_path.parent / f"{output_path.stem}_temp.geojson"
    
    try:
        # Write temporary GeoJSON
        with open(temp_geojson, 'w') as f:
            json.dump(features, f)
        
        # Use tippecanoe to generate PMTiles
        # Note: This requires tippecanoe to be installed
        import subprocess
        
        cmd = [
            "tippecanoe",
            "-o", str(output_path),
            "-z", str(maxzoom),
            "-Z", str(minzoom),
            "--force",
            "--no-tile-compression",
            "--drop-densest-as-needed",
            str(temp_geojson)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise RuntimeError(f"tippecanoe failed: {result.stderr}")
            
        logger.info(f"Generated PMTiles: {output_path}")
        
    finally:
        # Clean up temporary file
        if temp_geojson.exists():
            temp_geojson.unlink()


def create_feature_summary(features: Dict[str, Any]) -> Dict[str, Any]:
    """Create a summary of ingested features."""
    feature_list = features.get("features", [])
    
    summary = {
        "total_features": len(feature_list),
        "feature_types": {},
        "properties": set(),
        "has_feature_ids": 0
    }
    
    for feature in feature_list:
        # Count geometry types
        geom_type = feature.get("geometry", {}).get("type", "Unknown")
        summary["feature_types"][geom_type] = summary["feature_types"].get(geom_type, 0) + 1
        
        # Collect property names
        props = feature.get("properties", {})
        summary["properties"].update(props.keys())
        
        # Check for feature_id
        if "feature_id" in props:
            summary["has_feature_ids"] += 1
    
    # Convert set to sorted list for JSON serialization
    summary["properties"] = sorted(list(summary["properties"]))
    
    return summary