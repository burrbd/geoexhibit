"""Demo analyzer that generates sample COG outputs for testing and demonstration."""

import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.transform import from_bounds
from shapely.geometry import shape

from .analyzer import Analyzer, AnalyzerOutput, AssetSpec
from .timespan import TimeSpan


class DemoAnalyzer(Analyzer):
    """Demo analyzer that creates a simple raster based on the input geometry."""

    def __init__(self, output_dir: Optional[Path] = None):
        """Initialize the demo analyzer."""
        self.output_dir = output_dir or Path(tempfile.mkdtemp())
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @property
    def name(self) -> str:
        """Name of this analyzer."""
        return "demo_analyzer"

    def analyze(self, feature: Dict[str, Any], timespan: TimeSpan) -> AnalyzerOutput:
        """Analyze a feature and generate a simple COG."""
        feature_id = feature["properties"].get("feature_id", "unknown")

        cog_path = self._generate_cog(feature, timespan, feature_id)

        primary_asset = AssetSpec(
            key="analysis.tif",
            href=str(cog_path),
            title="Demo Analysis Result",
            description=f"Demo analysis result for feature {feature_id}",
            media_type="image/tiff; application=geotiff; profile=cloud-optimized",
            roles=["primary"],
        )

        extra_properties = {
            "geoexhibit:analyzer": self.name,
            "geoexhibit:analysis_time": timespan.start.isoformat(),
            "geoexhibit:synthetic": True,
            "demo:pixel_count": 256 * 256,
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
        output_path = self.output_dir / f"{feature_id}_{timestamp}_analysis.tif"

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
        """Generate synthetic raster data."""
        minx, miny, maxx, maxy = bounds
        x = np.linspace(minx, maxx, width)
        y = np.linspace(maxy, miny, height)
        xx, yy = np.meshgrid(x, y)

        centroid = geom.centroid
        cx, cy = centroid.x, centroid.y

        distances = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)

        day_of_year = timespan.start.timetuple().tm_yday
        time_factor = np.sin(day_of_year * 2 * np.pi / 365) * 0.3 + 1.0

        base_values = np.cos(distances * 10) * np.exp(-distances * 2) * time_factor

        noise = np.random.normal(0, 0.1, base_values.shape)
        data = base_values + noise

        data = np.clip(data, -1, 1)

        mask = distances > 0.5
        data[mask] = -9999

        return data.astype(np.float32)


def create_demo_analyzer(output_dir: Optional[Path] = None) -> DemoAnalyzer:
    """Create a demo analyzer instance."""
    return DemoAnalyzer(output_dir)
