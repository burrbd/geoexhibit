# GeoExhibit

[![CI](https://github.com/burrbd/geoexhibit/actions/workflows/ci.yml/badge.svg)](https://github.com/burrbd/geoexhibit/actions/workflows/ci.yml)
[![Coverage](https://img.shields.io/badge/coverage-96%25-brightgreen)](https://github.com/burrbd/geoexhibit)

A minimal, test-driven Python toolkit for publishing static STAC metadata and raster outputs to S3 with static Leaflet map scaffolding.

## 🚀 Quick Start

1. **Create configuration:**
   ```bash
   geoexhibit config --create
   # Edit config.json with your S3 bucket and settings
   ```

2. **Add your features:**
   ```bash
   # Place your features in: features.json, features.geojson, data.json, etc.
   # Supports: GeoJSON, NDJSON, GeoPackage, Shapefile
   ```

3. **Run the pipeline:**
   ```bash
   geoexhibit run config.json
   # Default: publishes to S3
   # Local output: geoexhibit run config.json --local-out ./output
   ```

4. **View your map:**
   ```bash
   # Open web_scaffold/index.html in browser
   # Point to your published STAC collection
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
The repo includes `examples/config.json` with fire analysis settings:

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
The repo includes `features.json` with 3 sample fire areas:
- Fire Area A (Sept 15, 2023) - Polygon in South Australia  
- Fire Area B (Oct 2, 2023) - Polygon with moderate severity
- Fire Point (Nov 20, 2023) - Point location with low severity

### Step 5: Run the Demo
```bash
# Publish to S3 (default)
geoexhibit run examples/config.json

# Or test locally first
geoexhibit run examples/config.json --local-out ./demo_output

# Preview without executing
geoexhibit run examples/config.json --dry-run
```

### Step 6: Verify Results
```bash
# The pipeline outputs a job ID like: 01K4XQ0N2DB35WHWZCAK3H0WAT
# Verify the published structure:
python verify_aws_publishing.py examples/config.json <job_id>
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
1. **Loads 3 fire features** from `features.json`
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
- 95%+ test coverage requirement
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

**Coverage**: Currently **96%+** across all modules

## 📚 Examples

See `examples/` directory:
- `config.json` - Complete configuration example
- `features.json` - Sample fire analysis features

## 🔗 Links

- **STAC Specification**: https://stacspec.org/
- **TiTiler**: https://developmentseed.org/titiler/
- **PMTiles**: https://github.com/protomaps/PMTiles

## 📄 License

MIT