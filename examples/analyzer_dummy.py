"""Dummy analyzer that generates sample COG outputs for testing and demonstration."""

import logging
import tempfile
from pathlib import Path
from typing import Dict, Any

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.transform import from_bounds
from shapely.geometry import shape, box
from shapely.ops import transform
import pyproj

from geoexhibit.core.interfaces import Analyzer, AnalyzerOutput, AssetSpec, TimeSpan

logger = logging.getLogger(__name__)


class DummyAnalyzer(Analyzer):
    """
    Dummy analyzer that creates a simple raster based on the input geometry.
    Generates a small COG with synthetic data for testing purposes.
    """
    
    def __init__(self, output_dir: Path):
        """
        Initialize the dummy analyzer.
        
        Args:
            output_dir: Directory to write output files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    @property
    def name(self) -> str:
        """Name of this analyzer."""
        return "dummy_analyzer"
    
    def analyze(self, feature: Dict[str, Any], timespan: TimeSpan) -> AnalyzerOutput:
        """
        Analyze a feature and generate a simple COG.
        
        Args:
            feature: GeoJSON feature
            timespan: Time span for analysis
            
        Returns:
            AnalyzerOutput with primary COG asset and optional thumbnail
        """
        feature_id = feature["properties"].get("feature_id", "unknown")
        logger.info(f"Analyzing feature {feature_id} for time {timespan.start}")
        
        # Generate the primary COG
        cog_path = self._generate_cog(feature, timespan)
        
        # Generate optional thumbnail
        thumbnail_path = self._generate_thumbnail(feature, timespan)
        
        # Create primary COG asset spec
        primary_asset = AssetSpec(
            key="analysis",  # This becomes the asset key in STAC
            href=str(cog_path),  # Local path - will be resolved by publisher
            title="Analysis Result",
            description=f"Dummy analysis result for feature {feature_id}",
            media_type="image/tiff; application=geotiff; profile=cloud-optimized",
            roles=["data"]  # Publisher will add "primary" role
        )
        
        # Create additional assets (thumbnail)
        additional_assets = []
        if thumbnail_path:
            thumbnail_asset = AssetSpec(
                key="thumbnail.png",
                href=str(thumbnail_path),
                title="Thumbnail",
                description="Preview thumbnail",
                media_type="image/png",
                roles=["thumbnail"]
            )
            additional_assets.append(thumbnail_asset)
        
        # Add some extra properties to the STAC item
        extra_properties = {
            "geoexhibit:analyzer": self.name,
            "geoexhibit:analysis_time": timespan.start.isoformat(),
            "geoexhibit:synthetic": True,
            "dummy:pixel_count": 256 * 256  # Synthetic property
        }
        
        return AnalyzerOutput(
            primary_cog_asset=primary_asset,
            additional_assets=additional_assets,
            extra_properties=extra_properties
        )
    
    def _generate_cog(self, feature: Dict[str, Any], timespan: TimeSpan) -> Path:
        """Generate a Cloud Optimized GeoTIFF for the feature."""
        feature_id = feature["properties"].get("feature_id", "unknown")
        
        # Get feature geometry and bounds
        geom = shape(feature["geometry"])
        bounds = geom.bounds  # (minx, miny, maxx, maxy)
        
        # Add some padding to the bounds
        padding = max(abs(bounds[2] - bounds[0]), abs(bounds[3] - bounds[1])) * 0.1
        padded_bounds = (
            bounds[0] - padding,
            bounds[1] - padding, 
            bounds[2] + padding,
            bounds[3] + padding
        )
        
        # Create output path
        timestamp = timespan.start.strftime("%Y%m%d_%H%M%S")
        output_path = self.output_dir / f"{feature_id}_{timestamp}_analysis.tif"
        
        # Create synthetic raster data
        width, height = 256, 256
        transform = from_bounds(*padded_bounds, width, height)
        
        # Generate synthetic data based on geometry and time
        data = self._generate_synthetic_data(geom, padded_bounds, width, height, timespan)
        
        # Write COG
        profile = {
            'driver': 'GTiff',
            'dtype': 'float32',
            'nodata': -9999,
            'width': width,
            'height': height,
            'count': 1,
            'crs': CRS.from_epsg(4326),
            'transform': transform,
            'tiled': True,
            'blockxsize': 256,
            'blockysize': 256,
            'compress': 'lzw',
            'predictor': 2,
            'BIGTIFF': 'IF_SAFER'
        }
        
        # Add COG-specific options
        creation_options = {
            'TILED': 'YES',
            'COMPRESS': 'LZW',
            'PREDICTOR': '2',
            'BIGTIFF': 'IF_SAFER'
        }
        
        with rasterio.open(output_path, 'w', **profile, **creation_options) as dst:
            dst.write(data, 1)
            
            # Add overviews for COG
            dst.build_overviews([2, 4, 8, 16], rasterio.enums.Resampling.average)
            dst.update_tags(ns='rio_overview', resampling='average')
        
        logger.debug(f"Generated COG: {output_path}")
        return output_path
    
    def _generate_synthetic_data(self, geom, bounds, width, height, timespan: TimeSpan) -> np.ndarray:
        """Generate synthetic raster data."""
        # Create coordinate arrays
        minx, miny, maxx, maxy = bounds
        x = np.linspace(minx, maxx, width)
        y = np.linspace(maxy, miny, height)  # Note: y is flipped for raster
        xx, yy = np.meshgrid(x, y)
        
        # Generate base pattern (distance from geometry centroid)
        centroid = geom.centroid
        cx, cy = centroid.x, centroid.y
        
        # Distance-based pattern
        distances = np.sqrt((xx - cx)**2 + (yy - cy)**2)
        
        # Add time-based variation (using day of year)
        day_of_year = timespan.start.timetuple().tm_yday
        time_factor = np.sin(day_of_year * 2 * np.pi / 365) * 0.3 + 1.0
        
        # Create synthetic values (e.g., simulating some analysis like NDVI)
        base_values = np.cos(distances * 10) * np.exp(-distances * 2) * time_factor
        
        # Add some noise
        noise = np.random.normal(0, 0.1, base_values.shape)
        data = base_values + noise
        
        # Normalize to reasonable range (e.g., -1 to 1 like NDVI)
        data = np.clip(data, -1, 1)
        
        # Set nodata outside geometry bounds (simplified)
        # For a full implementation, you'd properly mask using the geometry
        mask = distances > 0.5  # Simple distance-based mask
        data[mask] = -9999
        
        return data.astype(np.float32)
    
    def _generate_thumbnail(self, feature: Dict[str, Any], timespan: TimeSpan) -> Path:
        """Generate a PNG thumbnail for the analysis."""
        try:
            from PIL import Image
            import matplotlib.pyplot as plt
            import matplotlib.patches as patches
            from matplotlib.colors import Normalize
            import io
        except ImportError:
            logger.warning("PIL/matplotlib not available, skipping thumbnail generation")
            return None
        
        feature_id = feature["properties"].get("feature_id", "unknown")
        timestamp = timespan.start.strftime("%Y%m%d_%H%M%S")
        thumbnail_path = self.output_dir / f"{feature_id}_{timestamp}_thumbnail.png"
        
        # Get feature geometry
        geom = shape(feature["geometry"])
        bounds = geom.bounds
        
        # Create a simple visualization
        fig, ax = plt.subplots(1, 1, figsize=(4, 4), dpi=100)
        
        # Draw the geometry
        if geom.geom_type == 'Polygon':
            x, y = geom.exterior.xy
            ax.plot(x, y, color='red', linewidth=2, label='Feature')
            ax.fill(x, y, alpha=0.3, color='red')
        elif geom.geom_type == 'Point':
            ax.scatter([geom.x], [geom.y], color='red', s=100, label='Feature')
        else:
            # Handle other geometry types with bounding box
            minx, miny, maxx, maxy = bounds
            rect = patches.Rectangle((minx, miny), maxx-minx, maxy-miny,
                                   linewidth=2, edgecolor='red', facecolor='red', alpha=0.3)
            ax.add_patch(rect)
        
        # Set bounds with padding
        padding = max(abs(bounds[2] - bounds[0]), abs(bounds[3] - bounds[1])) * 0.1
        ax.set_xlim(bounds[0] - padding, bounds[2] + padding)
        ax.set_ylim(bounds[1] - padding, bounds[3] + padding)
        
        # Add title and formatting
        ax.set_title(f"Analysis Preview\n{timespan.start.strftime('%Y-%m-%d')}", fontsize=10)
        ax.set_aspect('equal')
        ax.grid(True, alpha=0.3)
        
        # Save thumbnail
        plt.tight_layout()
        plt.savefig(thumbnail_path, dpi=100, bbox_inches='tight', 
                   facecolor='white', edgecolor='none')
        plt.close()
        
        logger.debug(f"Generated thumbnail: {thumbnail_path}")
        return thumbnail_path


def create_dummy_analyzer(output_dir: Path) -> DummyAnalyzer:
    """
    Create a dummy analyzer instance.
    
    Args:
        output_dir: Directory for output files
        
    Returns:
        Configured DummyAnalyzer
    """
    return DummyAnalyzer(output_dir)