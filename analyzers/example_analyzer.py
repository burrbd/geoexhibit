"""Example analyzer plugin demonstrating external plugin development."""

import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.transform import from_bounds
from shapely.geometry import shape

# Import GeoExhibit components
from geoexhibit.analyzer import Analyzer, AnalyzerOutput, AssetSpec
from geoexhibit.timespan import TimeSpan
from geoexhibit import plugin_registry


@plugin_registry.register("example")
class ExampleAnalyzer(Analyzer):
    """
    Example custom analyzer for demonstration.
    
    This analyzer generates a different synthetic pattern than DemoAnalyzer,
    showing how users can create their own analysis logic.
    """

    def __init__(self, output_dir: Optional[Path] = None):
        """Initialize the example analyzer."""
        self.output_dir = output_dir or Path(tempfile.mkdtemp())
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @property
    def name(self) -> str:
        """Name of this analyzer."""
        return "example_analyzer"

    def analyze(self, feature: Dict[str, Any], timespan: TimeSpan) -> AnalyzerOutput:
        """
        Analyze a feature and generate a custom COG with different pattern than demo.
        
        This example creates a radial gradient pattern instead of the cosine 
        pattern used by DemoAnalyzer.
        """
        feature_id = feature["properties"].get("feature_id", "unknown")

        cog_path = self._generate_custom_cog(feature, timespan, feature_id)

        primary_asset = AssetSpec(
            key="analysis",
            href=str(cog_path),
            title="Example Analysis Result",
            description=f"Custom analysis result for feature {feature_id}",
            media_type="image/tiff; application=geotiff; profile=cloud-optimized",
            roles=["data", "primary"],
        )

        # Custom properties specific to this analyzer
        extra_properties = {
            "geoexhibit:analyzer": self.name,
            "geoexhibit:analysis_time": timespan.start.isoformat(),
            "example:pattern_type": "radial_gradient",
            "example:custom_param": 42,
            "example:algorithm_version": "1.0.0",
        }

        return AnalyzerOutput(
            primary_cog_asset=primary_asset,
            extra_properties=extra_properties,
        )

    def _generate_custom_cog(
        self, feature: Dict[str, Any], timespan: TimeSpan, feature_id: str
    ) -> Path:
        """Generate a Cloud Optimized GeoTIFF with custom radial gradient pattern."""
        geom = shape(feature["geometry"])
        bounds = geom.bounds

        # Slightly larger padding for this example
        padding = max(abs(bounds[2] - bounds[0]), abs(bounds[3] - bounds[1])) * 0.15
        padded_bounds = (
            bounds[0] - padding,
            bounds[1] - padding,
            bounds[2] + padding,
            bounds[3] + padding,
        )

        timestamp = timespan.start.strftime("%Y%m%d_%H%M%S")
        output_path = self.output_dir / f"{feature_id}_{timestamp}_example.tif"

        width, height = 512, 512  # Higher resolution than demo
        transform = from_bounds(*padded_bounds, width, height)

        data = self._generate_radial_gradient_data(
            geom, padded_bounds, width, height, timespan
        )

        # COG profile optimized for this analyzer
        profile = {
            "driver": "GTiff",
            "dtype": "float32",
            "nodata": -9999,
            "width": width,
            "height": height,
            "count": 1,
            "crs": CRS.from_epsg(4326),
            "transform": transform,
            "tiled": True,
            "blockxsize": 256,
            "blockysize": 256,
            "compress": "lzw",
            "predictor": 2,
        }

        with rasterio.Env(GDAL_TIFF_OVR_BLOCKSIZE=256):
            with rasterio.open(output_path, "w", **profile) as dst:
                dst.write(data, 1)
                dst.build_overviews([2, 4, 8, 16], rasterio.enums.Resampling.average)
                dst.update_tags(ns="rio_overview", resampling="average")

        return output_path

    def _generate_radial_gradient_data(
        self,
        geom: Any,
        bounds: tuple[float, float, float, float],
        width: int,
        height: int,
        timespan: TimeSpan,
    ) -> Any:
        """Generate synthetic raster data with radial gradient pattern."""
        minx, miny, maxx, maxy = bounds
        x = np.linspace(minx, maxx, width)
        y = np.linspace(maxy, miny, height)
        xx, yy = np.meshgrid(x, y)

        centroid = geom.centroid
        cx, cy = centroid.x, centroid.y

        # Create radial distances from centroid
        distances = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
        max_distance = np.max(distances)
        normalized_distances = distances / max_distance

        # Time-based variation (different from demo)
        day_of_year = timespan.start.timetuple().tm_yday
        seasonal_factor = np.cos(day_of_year * 2 * np.pi / 365) * 0.5 + 1.0

        # Create radial gradient with seasonal variation
        gradient_values = (1.0 - normalized_distances) * seasonal_factor
        
        # Add some noise for realism
        noise = np.random.normal(0, 0.05, gradient_values.shape)
        data = gradient_values + noise

        # Clip values to reasonable range
        data = np.clip(data, 0, 2)

        # Mask areas outside reasonable distance from feature
        mask = normalized_distances > 0.8
        data[mask] = -9999

        return data.astype(np.float32)


# Helper function for easy instantiation (following GeoExhibit patterns)
def create_example_analyzer(output_dir: Optional[Path] = None) -> ExampleAnalyzer:
    """Create an example analyzer instance."""
    return ExampleAnalyzer(output_dir)