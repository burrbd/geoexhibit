"""Simple example analyzer plugin for GeoExhibit without heavy dependencies."""

import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

from geoexhibit.analyzer import Analyzer, AnalyzerOutput, AssetSpec
from geoexhibit.plugin_registry import register
from geoexhibit.timespan import TimeSpan


@register("simple_example")
class SimpleExampleAnalyzer(Analyzer):
    """Simple example analyzer that demonstrates the plugin system without dependencies.
    
    This analyzer creates a mock analysis output without requiring rasterio, numpy,
    or other heavy dependencies. Perfect for testing the plugin system.
    """

    def __init__(self, output_format: str = "tiff", mock_value: float = 42.0):
        """Initialize the simple example analyzer.
        
        Args:
            output_format: Format of output file (just for demo)
            mock_value: Mock analysis value for demonstration
        """
        self.output_format = output_format
        self.mock_value = mock_value

    @property
    def name(self) -> str:
        """Name of this analyzer."""
        return "simple_example"

    def analyze(self, feature: Dict[str, Any], timespan: TimeSpan) -> AnalyzerOutput:
        """Analyze a feature and return mock analysis output."""
        feature_id = feature["properties"].get("feature_id", "unknown")
        
        # Create a temporary mock file path (would be real COG in production)
        temp_dir = Path(tempfile.gettempdir())
        timestamp = timespan.start.strftime("%Y%m%d_%H%M%S")
        mock_cog_path = temp_dir / f"{feature_id}_{timestamp}_simple_analysis.tif"

        primary_asset = AssetSpec(
            key="analysis",
            href=str(mock_cog_path),
            title=f"Simple Example Analysis ({self.output_format})",
            description=f"Mock analysis for feature {feature_id} with value {self.mock_value}",
            media_type="image/tiff; application=geotiff; profile=cloud-optimized",
            roles=["data", "primary"],
        )

        extra_properties = {
            "geoexhibit:analyzer": self.name,
            "geoexhibit:analysis_time": timespan.start.isoformat(),
            "geoexhibit:synthetic": True,
            "simple_example:output_format": self.output_format,
            "simple_example:mock_value": self.mock_value,
            "simple_example:feature_id": feature_id,
        }

        return AnalyzerOutput(
            primary_cog_asset=primary_asset,
            extra_properties=extra_properties,
        )