# GeoExhibit

[![CI](https://github.com/burrbd/geoexhibit/actions/workflows/ci.yml/badge.svg)](https://github.com/burrbd/geoexhibit/actions/workflows/ci.yml)
[![Coverage](https://img.shields.io/badge/coverage-96%25-brightgreen)](https://github.com/burrbd/geoexhibit)

A minimal, test-driven Python toolkit for publishing static STAC metadata and raster outputs to S3 with static Leaflet map scaffolding.

## 🚀 Quick Start

### Step 1: Install All Dependencies
```bash
# Core GeoExhibit package
pip install -e ".[dev]"

# Required for raster analysis and AWS publishing
pip install rasterio numpy shapely boto3 jsonschema

# Optional: PMTiles generation (requires tippecanoe)
# Ubuntu/Debian: sudo apt install tippecanoe
# macOS: brew install tippecanoe
# Windows: See https://github.com/mapbox/tippecanoe#installation

# Development tools setup (optional)
./setup_dev.sh
```

### Step 2: Create Configuration
```bash
geoexhibit config --create
# Edit config.json with your S3 bucket and settings
# See demo/config.json for reference
```

### Step 3: Add Your Features
```bash
# Place your features in: features.json, features.geojson, data.json, etc.
# Supports: GeoJSON, NDJSON, GeoPackage, Shapefile
# See demo/features.json for example fire analysis data
```

### Step 4: Publish STAC Analysis
```bash
# Configure AWS credentials
export AWS_ACCESS_KEY_ID="your_access_key"
export AWS_SECRET_ACCESS_KEY="your_secret_key" 
export AWS_DEFAULT_REGION="your_region"

# Publish to S3 (production)
geoexhibit run config.json

# OR test locally first
geoexhibit run config.json --local-out ./output

# Preview without executing
geoexhibit run config.json --dry-run
```

### Step 5: Deploy Infrastructure (Optional)
```bash
# For web map with TiTiler support
cd terraform/

# Install prerequisites (if needed)
make install-prerequisites  # AWS CLI v2, Terraform, Docker

# Set up AWS permissions
./setup-aws-permissions.sh

# Configure terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars if needed (uses ../examples/config.json by default)

# Deploy complete infrastructure
make deploy

# Get CloudFront URL for web map
terraform output cloudfront_url
```

### Step 6: Verify Published Data
Two verification tools are provided to validate your published STAC data:

#### AWS Publishing Verification
```bash
# The pipeline outputs a job ID like: 01K4XQ0N2DB35WHWZCAK3H0WAT
# Verify the complete S3 structure and STAC compliance:
python demo/test_aws_pipeline.py demo/config.json <job_id>

# This script checks:
# ✅ STAC Collection exists and is valid
# ✅ All STAC Items are properly structured
# ✅ Primary COG assets have correct roles ["data", "primary"]
# ✅ PMTiles file exists (if tippecanoe available)
# ✅ S3 bucket permissions and access
```

#### Infrastructure End-to-End Testing
```bash
# After deploying infrastructure, test complete steel thread:
python demo/test_stac_webmap_e2e.py https://YOUR_CLOUDFRONT_URL

# This script validates:
# ✅ STAC Collection loads via CloudFront
# ✅ PMTiles vector tiles accessible
# ✅ STAC Items load correctly
# ✅ TiTiler TileJSON generation works
# ✅ Raster tiles render properly
# ✅ Complete web map data flow
```

### Step 7: View Your Map
```bash
# Open web_scaffold/index.html in browser
# Configure with your CloudFront URL and job ID
# Use date slider to explore temporal analyses
# Click features to load TiTiler raster overlays
```

## 🔥 Demo: Fire Analysis Example

Here's a complete working example using the included demo data:

### Step 1: Install Dependencies
```bash
pip install -e ".[dev]"
pip install rasterio numpy shapely boto3 jsonschema

# For PMTiles generation (optional - demo works without it):
# Install tippecanoe: https://github.com/mapbox/tippecanoe#installation
# Ubuntu/Debian: apt install tippecanoe
# macOS: brew install tippecanoe
```

### Step 2: Configure AWS
```bash
export AWS_ACCESS_KEY_ID="your_access_key"
export AWS_SECRET_ACCESS_KEY="your_secret_key"
export AWS_DEFAULT_REGION="your_region"
```

### Step 3: Set Up Demo Configuration
The repo includes `demo/config.json` with fire analysis settings:

```json
{
  "project": {
    "name": "sa-fire-analyses",
    "collection_id": "fires_sa_demo",
    "title": "SA Fire Analyses Demo",
    "description": "Demo raster analyses across fire events"
  },
  "aws": {
    "s3_bucket": "your-bucket-name",
    "region": "ap-southeast-2"
  },
  "time": {
    "mode": "declarative",
    "extractor": "attribute_date",
    "field": "properties.fire_date",
    "format": "auto",
    "tz": "UTC"
  }
}
```

Update the `s3_bucket` to your bucket name.

### Step 4: Demo Features
The repo includes `demo/features.json` with 3 sample fire areas:
- Fire Area A (Sept 15, 2023) - Polygon in South Australia  
- Fire Area B (Oct 2, 2023) - Polygon with moderate severity
- Fire Point (Nov 20, 2023) - Point location with low severity

### Step 5: Run the Demo
```bash
# Publish to S3 (default)
geoexhibit run demo/config.json

# Or test locally first
geoexhibit run demo/config.json --local-out ./demo_output

# Preview without executing
geoexhibit run demo/config.json --dry-run
```

### Step 6: Verify Results
```bash
# The pipeline outputs a job ID like: 01K4XQ0N2DB35WHWZCAK3H0WAT
# Use the verification tools (see Step 6 above for detailed instructions):
python demo/test_aws_pipeline.py demo/config.json <job_id>
```

### Expected Output Structure
```
s3://your-bucket/jobs/<job_id>/
├── stac/
│   ├── collection.json              # STAC Collection with fire analyses  
│   └── items/
│       ├── <item_id_1>.json         # Fire Area A analysis item
│       ├── <item_id_2>.json         # Fire Area B analysis item  
│       └── <item_id_3>.json         # Fire Point analysis item
├── assets/
│   ├── <item_id_1>/analysis.tif     # Primary COG for Area A
│   ├── <item_id_2>/analysis.tif     # Primary COG for Area B
│   └── <item_id_3>/analysis.tif     # Primary COG for Fire Point
└── pmtiles/
    └── features.pmtiles             # Vector tiles (if tippecanoe available)
```

### Step 7: Explore with Web Map
```bash
# Open web_scaffold/index.html in browser
# Configure URLs to point to your published STAC collection
# Use date slider to explore temporal fire analyses
# Click features to load TiTiler raster overlays
```

### What the Demo Does
1. **Loads 3 fire features** from `demo/features.json`
2. **Extracts fire dates** using declarative time provider (`properties.fire_date`)  
3. **Generates synthetic COG analyses** using DemoAnalyzer (dNBR-style rasters)
4. **Creates STAC Collection + 3 Items** with proper primary COG assets
5. **Publishes to S3** under canonical `jobs/<job_id>/` layout
6. **Verifies structure** using AWS APIs for TiTiler compatibility

The generated COGs have:
- ✅ **Cloud-optimized structure** (tiling, overviews, compression)
- ✅ **Primary asset roles** `["data", "primary"]` for TiTiler auto-discovery
- ✅ **Fully qualified S3 URLs** for direct TiTiler access
- ✅ **Synthetic but realistic data** (NDVI-style values with time variation)

## 🏗️ Architecture

**One-shot CLI publishing** - Single command publishes complete STAC Collection + Items + COG files to S3:

```
geoexhibit run config.json
```

**Canonical S3/STAC Layout** (hard-coded, not user-configurable):
```
s3://<bucket>/jobs/<job_id>/
  stac/
    collection.json                        # Collection with relative links
    items/<item_id>.json                   # Items with primary COG assets
  pmtiles/features.pmtiles                 # Vector tiles for features  
  assets/<item_id>/<asset_name>.tif        # Primary COGs (S3 URLs in STAC)
  thumbs/<item_id>/*.png                   # Optional thumbnails
```

**HREF Rules** (enforced internally):
- **COG assets**: Fully qualified S3 URLs (`s3://bucket/key.tif`)
- **All other HREFs**: Strictly relative paths
- **Users never configure HREFs** - library enforces STAC + TiTiler compatibility

## 📦 Components

- **TimeProvider**: Extract time information from features (declarative config-driven)
- **Analyzer**: Generate raster outputs (ships with DemoAnalyzer for COG generation)
- **STAC Writer**: Create Collection + Items with canonical layout  
- **Publisher**: Upload to S3 with verification or local filesystem
- **Web Scaffold**: Leaflet map with PMTiles overlay + TiTiler integration

## 🎯 TiTiler Compatibility

Each STAC Item designates a **primary COG asset** with roles `["data", "primary"]` so TiTiler can auto-discover it:

```json
{
  "assets": {
    "analysis": {
      "href": "s3://bucket/jobs/01ARZ3/assets/01ARZ4/analysis.tif",
      "roles": ["data", "primary"],
      "type": "image/tiff; application=geotiff; profile=cloud-optimized"
    }
  }
}
```

## 🕒 Time Providers

**Declarative (default)** - Zero Python for common cases:
```json
{
  "time": {
    "mode": "declarative",
    "extractor": "attribute_date",
    "field": "properties.fire_date", 
    "format": "auto",
    "tz": "UTC"
  }
}
```

**Callable (advanced)** - Custom Python functions:
```json
{
  "time": {
    "mode": "callable", 
    "provider": "my_module.providers:custom_time_extractor"
  }
}
```

## 🔌 Custom Analyzers (Plugin System)

Create your own analyzer plugins for custom geospatial analysis:

### **Create Plugin Repository**
```bash
# 1. Create your repository
git clone https://github.com/yourusername/my-fire-analyzers.git
cd my-fire-analyzers

# 2. Install GeoExhibit  
echo "geoexhibit" > requirements.txt
pip install -r requirements.txt

# 3. Create your analyzer
# my_analyzer.py
from geoexhibit import plugin_registry
from geoexhibit.analyzer import Analyzer, AnalyzerOutput, AssetSpec

@plugin_registry.register("fire_severity")
class FireSeverityAnalyzer(Analyzer):
    @property
    def name(self) -> str:
        return "fire_severity_analyzer"
    
    def analyze(self, feature, timespan) -> AnalyzerOutput:
        # Your custom analysis logic here
        cog_path = self._generate_severity_cog(feature, timespan)
        
        return AnalyzerOutput(
            primary_cog_asset=AssetSpec(
                key="analysis",
                href=str(cog_path),
                title="Fire Severity Analysis",
                roles=["data", "primary"]
            )
        )

# 4. Configure to use your analyzer
# config.json
{
  "analyzer": {"name": "fire_severity"},
  // ... other config
}

# 5. Run your analysis
geoexhibit run config.json
```

### **Local Development**
```bash
# Create analyzers/ directory in your project
mkdir analyzers

# Add your plugin file: analyzers/my_analyzer.py
# Include @plugin_registry.register("name") decorator

# Update config.json: "analyzer": {"name": "name"}
geoexhibit run config.json
```

Plugins are auto-discovered from local `analyzers/` directories and pip-installed packages with entry points.

## 🗺️ Web Map Features

The included web scaffold provides:
- **PMTiles overlay** for vector features
- **Date slider** for temporal navigation
- **Feature picker** with click selection
- **TiTiler integration** for raster display
- **Relative STAC paths** for same-origin hosting

## 💾 Idempotency & Job Scoping

- **Every run creates new `job_id`** - no overwrites
- **Map can be repointed** to new Collection JSON path
- **Job-scoped paths** ensure clean separation between runs

## 🔧 Development

**Install:**
```bash
pip install -e ".[dev]"
./setup_dev.sh  # Sets up pre-commit hooks + linters
```

**Development rules** (enforced by pre-commit + CI):
- Commit discipline: one unit of code + test per commit
- Black formatting, ruff linting, mypy type checking
- Test coverage requirements enforced by pre-push hooks
- Conventional commits (no noise)

## 📋 CLI Commands

**Primary workflow:**
```bash
geoexhibit run config.json                    # Complete pipeline
geoexhibit run config.json --local-out ./out  # Local output
geoexhibit run config.json --dry-run          # Preview actions
```

**Configuration:**
```bash
geoexhibit config --create                    # Generate default config  
geoexhibit validate                          # Validate current setup
```

**Development helpers:**
```bash
geoexhibit features import input.shp         # Normalize to GeoJSON
geoexhibit features pmtiles features.json    # Generate PMTiles
```

## 🧪 Testing

```bash
pytest                    # Run all tests
pytest --cov=geoexhibit   # With coverage
pytest tests/test_*.py    # Specific test files
```

**Coverage**: See badge above for current coverage status

## 🔍 Verification Tools

GeoExhibit provides two specialized verification tools located in the `demo/` directory:

### AWS Pipeline Test (`demo/test_aws_pipeline.py`)
Validates STAC data published to S3 using AWS APIs:

```bash
python demo/test_aws_pipeline.py <config_file> <job_id>

# Example:
python demo/test_aws_pipeline.py demo/config.json 01K4XQ0N2DB35WHWZCAK3H0WAT
```

**What it checks:**
- ✅ S3 bucket access and permissions
- ✅ STAC Collection structure and validity
- ✅ STAC Items with proper geometry and properties
- ✅ Primary COG assets with TiTiler-compatible roles
- ✅ PMTiles file existence (when tippecanoe available)
- ✅ Canonical layout compliance (`jobs/<job_id>/` structure)

**Requirements:** Configured AWS credentials with S3 read access

### STAC → Web Map End-to-End Test (`demo/test_stac_webmap_e2e.py`)
Tests complete web map data flow through deployed infrastructure:

```bash
python demo/test_stac_webmap_e2e.py <cloudfront_url>

# Example:
python demo/test_stac_webmap_e2e.py https://d30uc1nx5aa6eq.cloudfront.net
```

**What it tests:**
- ✅ STAC Collection loads via CloudFront → S3 routing
- ✅ PMTiles vector tiles accessible and properly formatted
- ✅ STAC Items load correctly with valid COG asset references
- ✅ TiTiler TileJSON generation (CloudFront → Lambda → S3 COGs)
- ✅ Raster tile rendering (XYZ pattern functionality)
- ✅ CORS headers and web map compatibility

**Requirements:** Deployed infrastructure (terraform) with published demo data

Both tools follow the steel thread methodology, testing the exact same data flow that the web map uses in production.

## 📚 Examples

See `demo/` directory:
- `config.json` - Complete configuration example
- `features.json` - Sample fire analysis features
- Verification and testing scripts

## 🔗 Links

- **STAC Specification**: https://stacspec.org/
- **TiTiler**: https://developmentseed.org/titiler/
- **PMTiles**: https://github.com/protomaps/PMTiles

## 📄 License

MIT