"""Example analyzer plugin demonstrating the GeoExhibit plugin system."""

import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.transform import from_bounds
from shapely.geometry import shape

from geoexhibit.analyzer import Analyzer, AnalyzerOutput, AssetSpec
from geoexhibit.plugin_registry import register
from geoexhibit.timespan import TimeSpan


@register("example")
class ExampleAnalyzer(Analyzer):
    """Example analyzer plugin that creates a simple raster based on the input geometry.
    
    This is an example of how to create a custom analyzer plugin for GeoExhibit.
    It demonstrates the @register decorator pattern and produces synthetic
    but valid Cloud Optimized GeoTIFF outputs.
    """

    def __init__(self, output_dir: Optional[Path] = None, pattern: str = "waves"):
        """Initialize the example analyzer.
        
        Args:
            output_dir: Directory for output files (defaults to temp directory)
            pattern: Pattern type for synthetic data ("waves", "circles", "gradient")
        """
        self.output_dir = output_dir or Path(tempfile.mkdtemp())
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.pattern = pattern

    @property
    def name(self) -> str:
        """Name of this analyzer."""
        return "example"

    def analyze(self, feature: Dict[str, Any], timespan: TimeSpan) -> AnalyzerOutput:
        """Analyze a feature and generate a simple COG with configurable patterns."""
        feature_id = feature["properties"].get("feature_id", "unknown")

        cog_path = self._generate_cog(feature, timespan, feature_id)

        primary_asset = AssetSpec(
            key="analysis",
            href=str(cog_path),
            title=f"Example Analysis Result ({self.pattern})",
            description=f"Example analysis result using {self.pattern} pattern for feature {feature_id}",
            media_type="image/tiff; application=geotiff; profile=cloud-optimized",
            roles=["data", "primary"],
        )

        extra_properties = {
            "geoexhibit:analyzer": self.name,
            "geoexhibit:analysis_time": timespan.start.isoformat(),
            "geoexhibit:synthetic": True,
            "example:pattern": self.pattern,
            "example:pixel_count": 256 * 256,
        }

        return AnalyzerOutput(
            primary_cog_asset=primary_asset,
            extra_properties=extra_properties,
        )

    def _generate_cog(
        self, feature: Dict[str, Any], timespan: TimeSpan, feature_id: str
    ) -> Path:
        """Generate a Cloud Optimized GeoTIFF for the feature."""
        geom = shape(feature["geometry"])
        bounds = geom.bounds

        padding = max(abs(bounds[2] - bounds[0]), abs(bounds[3] - bounds[1])) * 0.1
        padded_bounds = (
            bounds[0] - padding,
            bounds[1] - padding,
            bounds[2] + padding,
            bounds[3] + padding,
        )

        timestamp = timespan.start.strftime("%Y%m%d_%H%M%S")
        output_path = self.output_dir / f"{feature_id}_{timestamp}_example_{self.pattern}.tif"

        width, height = 256, 256
        transform = from_bounds(*padded_bounds, width, height)

        data = self._generate_synthetic_data(
            geom, padded_bounds, width, height, timespan
        )

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
                dst.build_overviews([2, 4, 8], rasterio.enums.Resampling.average)
                dst.update_tags(ns="rio_overview", resampling="average")

        return output_path

    def _generate_synthetic_data(
        self,
        geom: Any,
        bounds: tuple[float, float, float, float],
        width: int,
        height: int,
        timespan: TimeSpan,
    ) -> Any:
        """Generate synthetic raster data based on the configured pattern."""
        minx, miny, maxx, maxy = bounds
        x = np.linspace(minx, maxx, width)
        y = np.linspace(maxy, miny, height)
        xx, yy = np.meshgrid(x, y)

        centroid = geom.centroid
        cx, cy = centroid.x, centroid.y

        distances = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)

        # Time-based variation
        day_of_year = timespan.start.timetuple().tm_yday
        time_factor = np.sin(day_of_year * 2 * np.pi / 365) * 0.3 + 1.0

        # Generate different patterns based on configuration
        if self.pattern == "waves":
            base_values = np.cos(distances * 10) * np.exp(-distances * 2) * time_factor
        elif self.pattern == "circles":
            base_values = np.sin(distances * 5) * np.exp(-distances * 1.5) * time_factor
        elif self.pattern == "gradient":
            # Gradient from center outward
            base_values = np.exp(-distances * 3) * time_factor
        else:
            # Default to waves
            base_values = np.cos(distances * 10) * np.exp(-distances * 2) * time_factor

        # Add some noise
        noise = np.random.normal(0, 0.1, base_values.shape)
        data = base_values + noise

        # Clip values
        data = np.clip(data, -1, 1)

        # Mask areas outside reasonable distance
        mask = distances > 0.5
        data[mask] = -9999

        return data.astype(np.float32)