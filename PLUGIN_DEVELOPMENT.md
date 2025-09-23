# GeoExhibit Plugin Development Guide

This guide shows how to create your own analyzer plugins for GeoExhibit, enabling you to build custom geospatial analysis workflows.

## 🚀 Quick Start: Create Your Own Plugin Repository

The main use case for GeoExhibit plugins is creating your own GitHub repository with custom analyzers. Here's how:

### Step 1: Create Your Repository

```bash
# Create a new repository on GitHub
git clone https://github.com/yourusername/my-geoexhibit-analyzers.git
cd my-geoexhibit-analyzers
```

### Step 2: Install GeoExhibit

```bash
# Create requirements.txt
echo "geoexhibit" > requirements.txt
echo "numpy" >> requirements.txt  
echo "rasterio" >> requirements.txt
# Add other analysis dependencies...

# Install dependencies
pip install -r requirements.txt
```

### Step 3: Create Your Analyzer

Create `my_analyzer.py`:

```python
"""Custom fire severity analyzer using dNBR methodology."""

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


@plugin_registry.register("fire_severity")
class FireSeverityAnalyzer(Analyzer):
    """
    Custom analyzer for fire severity analysis using dNBR.
    
    This analyzer demonstrates how to create custom analysis logic
    for real-world fire severity assessment.
    """

    def __init__(self, output_dir: Optional[Path] = None):
        """Initialize the fire severity analyzer."""
        self.output_dir = output_dir or Path(tempfile.mkdtemp())
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @property
    def name(self) -> str:
        """Name of this analyzer."""
        return "fire_severity_analyzer"

    def analyze(self, feature: Dict[str, Any], timespan: TimeSpan) -> AnalyzerOutput:
        """
        Analyze fire severity for a feature using dNBR methodology.
        
        This example shows the structure - in practice, you would:
        1. Access satellite imagery (Landsat, Sentinel)
        2. Calculate pre/post-fire NBR
        3. Compute dNBR (difference NBR)
        4. Classify severity levels
        5. Generate COG output
        """
        feature_id = feature["properties"].get("feature_id", "unknown")
        severity = feature["properties"].get("severity", "unknown")

        # Generate your analysis COG
        cog_path = self._generate_severity_cog(feature, timespan, feature_id, severity)

        primary_asset = AssetSpec(
            key="analysis",
            href=str(cog_path),
            title="Fire Severity Analysis (dNBR)",
            description=f"Fire severity analysis for {feature_id} using dNBR methodology",
            media_type="image/tiff; application=geotiff; profile=cloud-optimized",
            roles=["data", "primary"],
        )

        # Add your custom metadata
        extra_properties = {
            "geoexhibit:analyzer": self.name,
            "geoexhibit:analysis_time": timespan.start.isoformat(),
            "fire:severity_class": severity,
            "fire:methodology": "dNBR",
            "fire:analysis_version": "2.1.0",
            "processing:software": "My Fire Analysis Pipeline v2.1",
        }

        return AnalyzerOutput(
            primary_cog_asset=primary_asset,
            extra_properties=extra_properties,
        )

    def _generate_severity_cog(
        self, feature: Dict[str, Any], timespan: TimeSpan, feature_id: str, severity: str
    ) -> Path:
        """Generate COG with fire severity analysis (implement your logic here)."""
        # This is where you'd implement your actual analysis logic
        # For demo purposes, create a simple output file
        
        timestamp = timespan.start.strftime("%Y%m%d_%H%M%S")
        output_path = self.output_dir / f"{feature_id}_{timestamp}_severity.tif"
        
        # TODO: Replace with your actual analysis:
        # 1. Access pre/post-fire imagery
        # 2. Calculate NBR bands
        # 3. Compute dNBR = NBR_prefire - NBR_postfire  
        # 4. Classify severity: unburned, low, moderate, high severity
        # 5. Write as COG with proper projection
        
        # For now, create a placeholder file
        output_path.touch()
        
        return output_path
```

### Step 4: Create Configuration

Create `config.json`:

```json
{
  "project": {
    "name": "my-fire-analyses",
    "collection_id": "custom_fire_analysis",
    "title": "Custom Fire Severity Analysis",
    "description": "Fire severity analysis using custom dNBR methodology"
  },
  "aws": {
    "s3_bucket": "your-bucket-name", 
    "region": "your-region"
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
    "geometry_in_item": true
  },
  "ids": {
    "strategy": "ulid",
    "prefix": "fire"
  },
  "time": {
    "mode": "declarative",
    "extractor": "attribute_date", 
    "field": "properties.fire_date",
    "format": "auto",
    "tz": "UTC"
  },
  "analyzer": {
    "name": "fire_severity"
  }
}
```

### Step 5: Add Your Features Data

Create `features.json` with your analysis areas:

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "properties": {
        "name": "Bushfire Area 1",
        "fire_date": "2023-12-15",
        "severity": "high"
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [[
          [151.0, -33.0],
          [151.1, -33.0], 
          [151.1, -32.9],
          [151.0, -32.9],
          [151.0, -33.0]
        ]]
      }
    }
  ]
}
```

### Step 6: Run Your Analysis

```bash
# Configure AWS credentials
export AWS_ACCESS_KEY_ID="your_access_key"
export AWS_SECRET_ACCESS_KEY="your_secret_key"
export AWS_DEFAULT_REGION="your_region"

# Run your custom analysis
geoexhibit run config.json

# Or test locally first
geoexhibit run config.json --local-out ./output
```

That's it! Your custom analyzer will be automatically discovered and used by GeoExhibit.

## 📦 Plugin Architecture Details

### Analyzer Interface

All analyzers must implement the `Analyzer` abstract base class:

```python
from geoexhibit.analyzer import Analyzer, AnalyzerOutput, AssetSpec
from geoexhibit.timespan import TimeSpan

class MyAnalyzer(Analyzer):
    @property
    def name(self) -> str:
        """Return analyzer name for logging/metadata."""
        return "my_custom_analyzer"
    
    def analyze(self, feature: Dict[str, Any], timespan: TimeSpan) -> AnalyzerOutput:
        """
        Analyze a feature at a specific time period.
        
        Args:
            feature: GeoJSON feature with geometry and properties
            timespan: Time period for analysis (instant or interval)
        
        Returns:
            AnalyzerOutput with primary COG asset and metadata
        """
        # Your analysis logic here
        return AnalyzerOutput(
            primary_cog_asset=AssetSpec(
                key="analysis",  # Asset key in STAC item
                href="/path/to/output.tif",  # Path to generated COG
                title="Analysis Result",
                description="Custom analysis output",
                media_type="image/tiff; application=geotiff; profile=cloud-optimized",
                roles=["data", "primary"]  # Required for TiTiler compatibility
            ),
            extra_properties={  # Optional metadata for STAC item
                "geoexhibit:analyzer": self.name,
                "custom:parameter": "value"
            }
        )
```

### Plugin Registration

Use the `@plugin_registry.register()` decorator:

```python
from geoexhibit import plugin_registry

@plugin_registry.register("my_plugin_name")
class MyAnalyzer(Analyzer):
    # Implementation here
    pass
```

### Plugin Discovery

GeoExhibit discovers plugins through **secure, controlled mechanisms only**:

1. **Local Development**: `analyzers/` directory in current working directory
2. **Pip Packages**: Entry points in `setup.py` using `geoexhibit.analyzers` group
3. **Direct Import**: Any module that imports and registers analyzers

**Security Note**: For safety and performance, GeoExhibit does **not** scan the entire Python path for analyzer modules. This prevents:
- Accidental import of unintended or malicious modules
- Performance degradation from broad filesystem scanning  
- Module name collisions that cause silent failures

For most users, simply importing your analyzer module (which happens when you run `geoexhibit run`) is sufficient.

## 🛠️ Advanced Plugin Features

### Parameterized Analyzers

Analyzers can accept parameters through their constructor:

```python
@plugin_registry.register("parameterized")
class ParameterizedAnalyzer(Analyzer):
    def __init__(self, resolution=30, algorithm="standard"):
        self.resolution = resolution
        self.algorithm = algorithm
    
    # ... implementation
```

Currently, parameters must be passed programmatically. Future versions may support config-driven parameters.

### Multiple Assets

Analyzers can generate multiple output assets:

```python
def analyze(self, feature, timespan) -> AnalyzerOutput:
    return AnalyzerOutput(
        primary_cog_asset=AssetSpec(
            key="severity",
            href="/path/to/severity.tif",
            roles=["data", "primary"]
        ),
        additional_assets=[
            AssetSpec(
                key="confidence",
                href="/path/to/confidence.tif", 
                roles=["data"]
            ),
            AssetSpec(
                key="thumbnail",
                href="/path/to/thumbnail.png",
                roles=["thumbnail"]
            )
        ]
    )
```

### Custom Metadata

Add custom properties to STAC items:

```python
extra_properties = {
    "geoexhibit:analyzer": self.name,
    "processing:datetime": datetime.utcnow().isoformat() + "Z",
    "processing:software": "My Analysis Pipeline v1.0",
    "custom:algorithm_version": "2.1.0",
    "custom:confidence_threshold": 0.85,
}
```

## 🧪 Testing Your Plugin

Create a simple test to verify your plugin works:

```python
# test_my_analyzer.py
import tempfile
from pathlib import Path
from datetime import datetime

from my_analyzer import FireSeverityAnalyzer
from geoexhibit.timespan import TimeSpan

def test_my_analyzer():
    with tempfile.TemporaryDirectory() as temp_dir:
        analyzer = FireSeverityAnalyzer(Path(temp_dir))
        
        # Test feature
        feature = {
            "type": "Feature",
            "properties": {"feature_id": "test_001", "severity": "moderate"},
            "geometry": {"type": "Point", "coordinates": [151.0, -33.0]}
        }
        
        # Test timespan  
        timespan = TimeSpan(start=datetime(2023, 12, 15))
        
        # Test analysis
        result = analyzer.analyze(feature, timespan)
        
        assert result.primary_cog_asset.key == "analysis"
        assert "fire:severity_class" in result.extra_properties
        assert result.extra_properties["fire:severity_class"] == "moderate"

if __name__ == "__main__":
    test_my_analyzer()
    print("✅ Plugin test passed!")
```

## 📚 Example Repositories

For complete examples, see:

- **Example Analyzer**: `/workspace/analyzers/example_analyzer.py` in the GeoExhibit repository
- **Demo Configuration**: `/workspace/demo/config.json` showing analyzer selection
- **Integration Tests**: `/workspace/tests/test_plugin_*.py` for testing patterns

## 🔍 Troubleshooting

### Plugin Not Found

```
PluginNotFoundError: Analyzer 'my_analyzer' not found. Available analyzers: ['demo']
```

**Solutions**:
1. Check that your analyzer module is imported (add `import my_analyzer` at the top level)
2. Verify the `@plugin_registry.register("my_analyzer")` decorator is applied
3. Ensure the name in config matches the registration name exactly

### Import Errors

```
Failed to import plugin /path/to/analyzer.py: No module named 'some_dependency'
```

**Solutions**:
1. Install missing dependencies: `pip install some_dependency`
2. Update your `requirements.txt` file
3. Check that all imports are available in your environment

### Analysis Failures

```
Failed to create analyzer 'my_analyzer': __init__() missing 1 required positional argument
```

**Solutions**:
1. Ensure your analyzer `__init__` method has sensible defaults for all parameters
2. Check that required parameters are provided (future versions will support config-driven parameters)

## 🤝 Contributing

We welcome contributions to improve the plugin system:

- Submit example analyzers for common use cases
- Improve plugin discovery mechanisms  
- Add config-driven parameter support
- Enhance error messages and debugging

Open an issue or pull request at [github.com/burrbd/geoexhibit](https://github.com/burrbd/geoexhibit).