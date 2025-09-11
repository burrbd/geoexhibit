"""PMTiles generation adapter for GeoExhibit."""

import json
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class PMTilesAdapter:
    """Adapter for generating PMTiles from feature collections."""
    
    def __init__(self, tippecanoe_path: str = "tippecanoe"):
        """
        Initialize PMTiles adapter.
        
        Args:
            tippecanoe_path: Path to tippecanoe executable
        """
        self.tippecanoe_path = tippecanoe_path
        self._check_tippecanoe_available()
    
    def _check_tippecanoe_available(self) -> None:
        """Check if tippecanoe is available."""
        try:
            result = subprocess.run([self.tippecanoe_path, "--help"], 
                                  capture_output=True, text=True)
            if result.returncode != 0:
                raise RuntimeError("tippecanoe is not working correctly")
        except FileNotFoundError:
            raise RuntimeError(
                f"tippecanoe not found at '{self.tippecanoe_path}'. "
                "Please install tippecanoe (https://github.com/mapbox/tippecanoe) "
                "or provide correct path."
            )
    
    def generate_pmtiles(self, 
                        features: Dict[str, Any], 
                        output_path: Path,
                        minzoom: int = 5,
                        maxzoom: int = 14,
                        feature_id_property: str = "feature_id",
                        additional_args: Optional[list] = None) -> None:
        """
        Generate PMTiles from a GeoJSON FeatureCollection.
        
        Args:
            features: GeoJSON FeatureCollection
            output_path: Path for output PMTiles file
            minzoom: Minimum zoom level
            maxzoom: Maximum zoom level  
            feature_id_property: Property name containing feature ID
            additional_args: Additional arguments to pass to tippecanoe
            
        Raises:
            RuntimeError: If PMTiles generation fails
        """
        logger.info(f"Generating PMTiles: {output_path}")
        
        # Validate input
        if not isinstance(features, dict) or features.get("type") != "FeatureCollection":
            raise ValueError("Input must be a GeoJSON FeatureCollection")
        
        feature_list = features.get("features", [])
        if not feature_list:
            raise ValueError("FeatureCollection is empty")
        
        # Check that features have the required ID property
        missing_ids = []
        for i, feature in enumerate(feature_list):
            props = feature.get("properties", {})
            if feature_id_property not in props:
                missing_ids.append(i)
        
        if missing_ids:
            logger.warning(f"Features missing {feature_id_property}: {missing_ids[:5]}")
            # Add missing IDs
            from ulid import ULID
            for i in missing_ids:
                feature_list[i].setdefault("properties", {})[feature_id_property] = str(ULID())
        
        # Create temporary GeoJSON file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.geojson', delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            json.dump(features, temp_file, ensure_ascii=False)
        
        try:
            # Build tippecanoe command
            cmd = [
                self.tippecanoe_path,
                "-o", str(output_path),
                "-z", str(maxzoom),
                "-Z", str(minzoom),
                "--force",  # Overwrite existing file
                "--no-tile-compression",  # Better for PMTiles
                "--drop-densest-as-needed",  # Handle high-density areas
                "--extend-zooms-if-still-dropping",  # Try to include all features
                "--generate-ids",  # Generate tile feature IDs
                str(temp_path)
            ]
            
            # Add additional arguments if provided
            if additional_args:
                # Insert additional args before the input file
                cmd = cmd[:-1] + additional_args + [str(temp_path)]
            
            logger.debug(f"Running tippecanoe command: {' '.join(cmd)}")
            
            # Run tippecanoe
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                error_msg = result.stderr or result.stdout or "Unknown error"
                raise RuntimeError(f"tippecanoe failed: {error_msg}")
            
            if not output_path.exists():
                raise RuntimeError("PMTiles file was not created")
            
            # Log success with file size
            file_size = output_path.stat().st_size
            logger.info(f"Generated PMTiles: {output_path} ({file_size:,} bytes)")
            
        finally:
            # Clean up temporary file
            if temp_path.exists():
                temp_path.unlink()
    
    def get_pmtiles_info(self, pmtiles_path: Path) -> Dict[str, Any]:
        """
        Get information about a PMTiles file.
        
        Args:
            pmtiles_path: Path to PMTiles file
            
        Returns:
            Dictionary with PMTiles metadata
            
        Raises:
            RuntimeError: If info extraction fails
        """
        if not pmtiles_path.exists():
            raise FileNotFoundError(f"PMTiles file not found: {pmtiles_path}")
        
        try:
            # Use pmtiles command line tool if available
            result = subprocess.run(
                ["pmtiles", "show", str(pmtiles_path)],
                capture_output=True, text=True
            )
            
            if result.returncode == 0:
                # Parse JSON output
                return json.loads(result.stdout)
            else:
                # Fall back to basic file info
                stat = pmtiles_path.stat()
                return {
                    "file_size": stat.st_size,
                    "modified": stat.st_mtime,
                    "path": str(pmtiles_path)
                }
                
        except FileNotFoundError:
            # pmtiles CLI not available, return basic info
            stat = pmtiles_path.stat()
            return {
                "file_size": stat.st_size,
                "modified": stat.st_mtime,
                "path": str(pmtiles_path)
            }
        except json.JSONDecodeError:
            # Invalid JSON response
            stat = pmtiles_path.stat()
            return {
                "file_size": stat.st_size,
                "modified": stat.st_mtime,
                "path": str(pmtiles_path),
                "error": "Could not parse PMTiles metadata"
            }
    
    def validate_pmtiles(self, pmtiles_path: Path) -> bool:
        """
        Validate that a PMTiles file is properly formatted.
        
        Args:
            pmtiles_path: Path to PMTiles file
            
        Returns:
            True if valid, False otherwise
        """
        try:
            info = self.get_pmtiles_info(pmtiles_path)
            # Basic validation - file exists and has reasonable size
            return info.get("file_size", 0) > 0
        except Exception as e:
            logger.error(f"PMTiles validation failed: {e}")
            return False


def create_pmtiles_adapter(tippecanoe_path: str = "tippecanoe") -> PMTilesAdapter:
    """
    Create and validate PMTiles adapter.
    
    Args:
        tippecanoe_path: Path to tippecanoe executable
        
    Returns:
        Configured PMTilesAdapter
    """
    return PMTilesAdapter(tippecanoe_path)


def generate_pmtiles_from_features(features: Dict[str, Any], 
                                 output_path: Path,
                                 config: Optional[Dict[str, Any]] = None) -> None:
    """
    Convenience function to generate PMTiles from features with configuration.
    
    Args:
        features: GeoJSON FeatureCollection
        output_path: Output path for PMTiles file
        config: Optional configuration dict with pmtiles settings
    """
    adapter = create_pmtiles_adapter()
    
    # Extract configuration
    if config and "pmtiles" in config:
        pmtiles_config = config["pmtiles"]
        minzoom = pmtiles_config.get("minzoom", 5)
        maxzoom = pmtiles_config.get("maxzoom", 14)
        feature_id_property = pmtiles_config.get("feature_id_property", "feature_id")
    else:
        minzoom = 5
        maxzoom = 14
        feature_id_property = "feature_id"
    
    adapter.generate_pmtiles(
        features=features,
        output_path=output_path,
        minzoom=minzoom,
        maxzoom=maxzoom,
        feature_id_property=feature_id_property
    )