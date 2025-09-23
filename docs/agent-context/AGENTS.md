
# GeoExhibit Technical Architecture

## 🏗️ **Core Architecture Overview**

GeoExhibit follows a **pipeline pattern** with clean separation of concerns:

```
Features → TimeProvider → Analyzer → STAC Writer → Publisher → S3/Local
    ↓           ↓            ↓           ↓           ↓
  GeoJSON   TimeSpans   AnalyzerOutput  STAC Items  Verification
```

## 📦 **Key Components**

### **Core Data Models** (`geoexhibit/`)
- **`timespan.py`**: `TimeSpan` - represents analysis time periods (instant or interval)
- **`analyzer.py`**: `AssetSpec`, `AnalyzerOutput`, `Analyzer` interface
- **`publish_plan.py`**: `PublishItem`, `PublishPlan` - orchestration data structures
- **`layout.py`**: `CanonicalLayout` - hard-coded S3/STAC path structure (users never configure)

### **Pipeline Components**
- **`config.py`**: Configuration loading/validation from JSON
- **`time_provider.py`**: Extract time information from features (interface)
- **`declarative_time.py`**: Config-driven time extraction (attribute_date, etc.)
- **`orchestrator.py`**: Coordinates feature×time iteration, creates PublishPlan
- **`stac_writer.py`**: Creates STAC Collection/Items with HREF rule enforcement
- **`publisher.py`**: S3Publisher + LocalPublisher with AWS verification
- **`pipeline.py`**: Main orchestration function `run_geoexhibit_pipeline()`
- **`cli.py`**: Click-based CLI interface

### **Demo Implementation**
- **`demo_analyzer.py`**: Generates synthetic COGs for testing/demonstration

## 🔄 **Data Flow**

### **1. Feature Loading**
```python
# pipeline.py
features = load_and_validate_features(features_file)
# → GeoJSON FeatureCollection with feature_id ensured
```

### **2. Time Extraction** 
```python
# orchestrator.py  
time_provider = DeclarativeTimeProvider(config.time_config)
time_spans = time_provider.for_feature(feature)
# → List[TimeSpan] per feature
```

### **3. Analysis Orchestration**
```python
# orchestrator.py
for feature in features:
    for timespan in time_spans:
        analyzer_output = analyzer.analyze(feature, timespan)
        item = PublishItem(ulid(), feature, timespan, analyzer_output)
# → PublishPlan with all items
```

### **4. STAC Generation**
```python
# stac_writer.py
collection = create_stac_collection(plan, config, layout)
items = [create_stac_item(publish_item, collection, config, layout)]
# → STAC Collection + Items with proper HREFs
```

### **5. Publishing**
```python
# publisher.py
publisher.publish_plan(plan)  # → S3 or local filesystem
publisher.verify_publication(plan)  # → AWS API verification
```

## 🛡️ **HREF Rule Enforcement**

**Critical Design**: HrefResolver in `stac_writer.py` enforces:
- **COG assets**: `s3://bucket/jobs/<job_id>/assets/<item_id>/<asset_name>`
- **All others**: Relative paths `../pmtiles/features.pmtiles`, `items/<item_id>.json`
- **Users never see/configure HREFs** - library handles automatically

```python
# stac_writer.py:HrefResolver
primary_href = resolver.resolve_cog_asset_href(item_id, asset_name)
# → "s3://bucket/jobs/123/assets/456/analysis.tif"

pmtiles_href = resolver.resolve_pmtiles_href()  
# → "../pmtiles/features.pmtiles"
```

## 🔌 **Plugin Points (for future enhancement)**

### **TimeProvider Plugin**
```python
# Callable mode in config
{"time": {"mode": "callable", "provider": "my_module:my_provider"}}

def my_provider(feature: dict) -> Iterable[TimeSpan]:
    # Custom time extraction logic
    return [TimeSpan(...)]
```

### **Analyzer Plugin** (planned)
```python
# Future plugin system
@analyzer.register("my_analyzer")
class MyAnalyzer(Analyzer):
    def analyze(self, feature, timespan) -> AnalyzerOutput:
        # Custom analysis logic
        return AnalyzerOutput(primary_cog_asset=...)
```

## 📁 **Canonical Layout (Hard-coded)**

**Never user-configurable** - supports infrastructure automation:

```
s3://bucket/jobs/<job_id>/
├── stac/
│   ├── collection.json              # Relative links to ../pmtiles/, items/
│   └── items/<item_id>.json         # S3 URLs for COGs, relative for others
├── pmtiles/features.pmtiles         # Vector tiles (if tippecanoe available)
├── assets/<item_id>/<asset>.tif     # Primary COGs (TiTiler-accessible)
└── thumbs/<item_id>/*.png           # Optional thumbnails
```

## 🧪 **Testing Strategy (London School TDD)**

### **Methodology (MANDATORY)**
- **London School TDD**: Focus on **behavior and inputs/outputs**, not implementation details
- **Unit tests**: Each component tested **in isolation with mocks** of collaborators
- **Mock all collaborators**: External services, dependencies, filesystem operations
- **Test contracts**: Verify what components do, not how they do it
- **Behavior verification**: Assert interactions with mocked collaborators

### **Test Types**
- **Unit tests**: Component isolation with comprehensive mocking
- **Integration tests**: End-to-end workflow with LocalPublisher (minimal, clearly labeled)
- **S3 mocking**: boto3 stubber for S3Publisher tests
- **CLI testing**: Click TestRunner for command validation
- **Coverage**: Requirement enforced by CI and pre-push hooks (never document percentages)

### **Examples**
```python
# ✅ CORRECT: Test behavior, mock collaborators
@patch('geoexhibit.publisher.boto3')
def test_publisher_uploads_files(mock_boto3):
    # Arrange: Mock dependencies
    mock_client = Mock()
    mock_boto3.client.return_value = mock_client
    
    # Act: Call the method
    publisher.publish_plan(plan)
    
    # Assert: Verify behavior (what happened)
    mock_client.upload_file.assert_called_with(expected_args)

# ❌ WRONG: Test implementation details
def test_publisher_internal_state():
    assert publisher._upload_count == 0  # Don't test internal state
```

## 🔧 **Development Patterns**

### **Dependency Injection**
```python
# publisher.py
def create_publisher(config, local_out_dir=None) -> Publisher:
    if local_out_dir:
        return LocalPublisher(local_out_dir, config)
    else:
        return S3Publisher(config)
```

### **Interface Abstractions**
```python
# All analyzers implement same interface
class Analyzer(ABC):
    @abstractmethod
    def analyze(self, feature, timespan) -> AnalyzerOutput: pass
    
    @property  
    @abstractmethod
    def name(self) -> str: pass
```

### **Configuration-Driven Behavior**
```python
# Declarative time extraction - no Python required
{
  "time": {
    "mode": "declarative",
    "extractor": "attribute_date",
    "field": "properties.fire_date"
  }
}
```

## 🚨 **Critical Implementation Notes**

1. **ULID Usage**: `from ulid import new as new_ulid; str(new_ulid())` - not `ULID()`
2. **PySTAC Extensions**: Must `add_to()` before `ext()` - `ProjectionExtension.add_to(item)`
3. **Import Strategy**: Heavy dependencies (numpy, rasterio) isolated in specific modules
4. **STAC Validation**: Requires `jsonschema` - make conditional for CI compatibility
5. **AWS Regions**: Optional in config, passed to boto3 client creation

## 🔧 **Development Environment Setup (CRITICAL)**

**⚠️ NEVER add `# type: ignore[import-not-found]` for runtime dependencies!**

### **Problem**: 
MyPy fails on imports like `from ulid import new as new_ulid` because development environment lacks runtime dependencies.

### **Correct Solution**:
```bash
# Install GeoExhibit in development mode (installs ALL dependencies)
pip install -e .

# Run development setup (includes above + hooks + linting tools)  
./setup_dev.sh
```

### **Wrong Solution** ❌:
```python
from ulid import new as new_ulid  # type: ignore[import-not-found]  # DON'T DO THIS
```

### **Why This Matters**:
- Runtime dependencies are declared in `pyproject.toml`
- MyPy needs actual modules to do proper type checking
- Type ignore comments mask real issues and pollute codebase
- Development environment must match runtime environment

### **Setup Verification**:
```bash
python3 -c "import ulid, pystac, boto3; print('✅ All deps available')"
mypy geoexhibit  # Should pass without type ignore comments
```

## 🎯 **Agent Context for GitHub Issues**

### **Working on Infrastructure (#2, #3)**
- Demo dataset already published: `s3://geoexhibit-demo/jobs/01K4XRE3K3KQDMTZ60XY1XWMN4/`
- Primary COGs have roles `["data", "primary"]` for TiTiler auto-discovery
- Web scaffold in `web_scaffold/` ready for TiTiler integration

### **Working on Plugin System (#4)**  
- `Analyzer` interface in `analyzer.py` - extend this pattern
- Look at `demo_analyzer.py` for implementation example
- `orchestrator.py:create_publish_plan()` handles analyzer instantiation

### **Working on Web Map (#5, #6)**
- Basic scaffold exists, needs PMTiles integration + TiTiler connectivity
- STAC Items have primary COG S3 URLs ready for TiTiler consumption
- Follow existing patterns in `web_scaffold/app.js`

### **Working on Real-World Analysis (#7)**
- Build on plugin system + COG helpers  
- Target: Google Earth Engine dNBR (burn severity analysis)
- Use `AnalyzerOutput` + `AssetSpec` patterns from `demo_analyzer.py`

## 📖 **Reference Documents**
- **README.md**: User documentation + demo instructions
- **DECISIONS.md**: 12 numbered implementation decisions with rationale
- **PROJECT_STATUS.md**: Current completion status + metrics
- **ROADMAP.md**: GitHub issues + dependency chain for next phases
- **PLAYBOOK.md**: Agent workflow guide for GitHub API integration

Rules are stored in .cursor/rules for Cursor registration.

## 🌐 **Steel Thread: Complete End-to-End Data Flow**

This section documents the complete steel thread implementation showing how the static web map, CloudFront, TiTiler (Lambda), and S3 interact for Issues #2 & #3.

### **Topology (CloudFront + Two Origins)**

- **Origin A (S3 "public")**: Hosts static site, STAC JSON, PMTiles, thumbnails. Accessed via CloudFront OAC (bucket is private; only CloudFront can read).
- **Origin B (Lambda URL)**: TiTiler app. CloudFront forwards `/stac/*` here. Lambda has IAM role with `s3:GetObject` on private COG paths (`s3://geoexhibit-demo/jobs/*`).

### **CloudFront Behaviors**
- `/jobs/*/stac/*` → Origin A (S3 via OAC) - STAC Collection and Items
- `/jobs/*/pmtiles/*.pmtiles` → Origin A (S3 via OAC) - Vector tiles
- `/stac/*` → Origin B (TiTiler Lambda) - Raster tile services
- `/*` → Origin A (S3 via OAC) - Default behavior for web app

### **CORS Configuration**
- **S3 static assets**: Allow Origin: `http://localhost:8000`; GET, HEAD methods
- **TiTiler**: Enable CORS for web map domain; responses include `Access-Control-Allow-Origin`

---

### **🚀 Page Load & PMTiles Overlay**

#### **1) Browser loads the app**
```
GET https://d30uc1nx5aa6eq.cloudfront.net/index.html (via web scaffold)
GET https://d30uc1nx5aa6eq.cloudfront.net/app.js
```
CloudFront → S3 (OAC). Cacheable (long TTL for static assets).

#### **2) App fetches the Collection**
```
GET https://d30uc1nx5aa6eq.cloudfront.net/jobs/01K55BB201KNAM8C3N9SF8TMEJ/stac/collection.json
```
CloudFront → S3 via `/jobs/*/stac/*` routing. Returns Collection with ID `fires_sa_demo`.

#### **3) App discovers PMTiles relative HREF**
From `collection.json`, relative link `../pmtiles/features.pmtiles` resolves to:
```
GET https://d30uc1nx5aa6eq.cloudfront.net/jobs/01K55BB201KNAM8C3N9SF8TMEJ/pmtiles/features.pmtiles
```
CloudFront → S3 via `/jobs/*/pmtiles/*.pmtiles` routing. Long-cache (16KB file). PMTiles JS library handles client-side ranging.

#### **4) User sees vector footprints**
- PMTiles client renders fire polygons client-side
- Each feature exposes `feature_id` in properties for click handling

---

### **🎯 Feature Click → STAC Item → Raster Tiles**

#### **5) User clicks a fire polygon**
App reads `feature_id` from PMTiles feature and computes Item HREF:
```
GET https://d30uc1nx5aa6eq.cloudfront.net/jobs/01K55BB201KNAM8C3N9SF8TMEJ/stac/items/01K55BB202VWS3XH5MPA0Z73WZ.json
```
CloudFront → S3 via `/jobs/*/stac/*` routing. Returns STAC Item with COG asset HREFs.

#### **6) Ask TiTiler for TileJSON**
Client requests TileJSON using the Item URL:
```
GET https://d30uc1nx5aa6eq.cloudfront.net/stac/tilejson.json
    ?url=https%3A%2F%2Fd30uc1nx5aa6eq.cloudfront.net%2Fjobs%2F01K55BB201KNAM8C3N9SF8TMEJ%2Fstac%2Fitems%2F01K55BB202VWS3XH5MPA0Z73WZ.json
    &assets=analysis
    &format=webp
```
CloudFront routes `/stac/*` → TiTiler (Lambda).

**TiTiler Process:**
1. Fetches Item JSON from CloudFront S3 origin (public STAC data)
2. Reads primary asset HREF: `s3://geoexhibit-demo/jobs/01K55BB201KNAM8C3N9SF8TMEJ/assets/01K55BB202VWS3XH5MPA0Z73WZ/analysis`
3. Uses Lambda IAM role to read COG directly from S3 (private data)
4. Returns TileJSON with tile URL template pointing back to TiTiler

**Example TileJSON Response:**
```json
{
  "tilejson": "2.2.0",
  "name": "analysis",
  "minzoom": 5,
  "maxzoom": 14,
  "bounds": [138.6, -35.1, 138.9, -34.9],
  "tiles": [
    "https://d30uc1nx5aa6eq.cloudfront.net/stac/tiles/{z}/{x}/{y}.webp?url=https%3A%2F%2Fd30uc1nx5aa6eq.cloudfront.net%2Fjobs%2F01K55BB201KNAM8C3N9SF8TMEJ%2Fstac%2Fitems%2F01K55BB202VWS3XH5MPA0Z73WZ.json&assets=analysis"
  ]
}
```

#### **7) Leaflet registers the raster layer**
App reads `tilejson.tiles[0]` template and adds as XYZ layer to map.

---

### **🗺️ Tile Fetches (XYZ Pattern)**

#### **8) Leaflet requests tiles during pan/zoom**
```
GET https://d30uc1nx5aa6eq.cloudfront.net/stac/tiles/10/902/637.webp
    ?url=https%3A%2F%2Fd30uc1nx5aa6eq.cloudfront.net%2Fjobs%2F01K55BB201KNAM8C3N9SF8TMEJ%2Fstac%2Fitems%2F01K55BB202VWS3XH5MPA0Z73WZ.json
    &assets=analysis
```

CloudFront → TiTiler (Lambda).

**TiTiler Tile Process:**
- Parses query params (Item URL + asset name)
- Opens same S3 COG using Lambda IAM role (internal access)
- Renders tile as WebP/PNG and streams back
- CloudFront caches tiles by path + full query string

---

### **📊 Sequence Diagram**

```
Browser           CloudFront            S3 (OAC)                TiTiler (Lambda)            S3 (private COGs)
   |                  |                      |                           |                          |
1) |-- index.html --->|---> (OAC) ---------->|                           |                          |
   |<-- app.js -------|<--- (cache) <--------|                           |                          |
2) |-- collection.json|---> (OAC) ---------->|                           |                          |
3) |-- features.pmtiles|---> (OAC) ---------->|                           |                          |
4) (user clicks fire polygon)                 |                           |                          |
5) |-- item.json ---->|---> (OAC) ---------->|                           |                          |
6) |-- TileJSON req ->|---------------------->TiTiler                    |                          |
   |                  |                      |---- GET item.json ------->|                          |
   |                  |                      |<--- STAC Item ------------|                          |
   |                  |                      |                           |-- GET s3://...COG ----->|
   |                  |                      |                           |<--- COG bytes ----------|
   |                  |<-- TileJSON response |                           |                          |
7) |-- tile z/x/y ----|---------------------->TiTiler                    |                          |
   |                  |                      |                           |-- read COG tile ------->|
   |                  |                      |                           |<--- rendered bytes -----|
   |<-- webp/png -----|<---------------------|                           |                          |
```

---

### **🌐 Actual URLs (GeoExhibit Implementation)**

**Collection:**
```
https://d30uc1nx5aa6eq.cloudfront.net/jobs/01K55BB201KNAM8C3N9SF8TMEJ/stac/collection.json
```

**PMTiles (from Collection relative link):**
```
https://d30uc1nx5aa6eq.cloudfront.net/jobs/01K55BB201KNAM8C3N9SF8TMEJ/pmtiles/features.pmtiles
```

**STAC Item:**
```
https://d30uc1nx5aa6eq.cloudfront.net/jobs/01K55BB201KNAM8C3N9SF8TMEJ/stac/items/01K55BB202VWS3XH5MPA0Z73WZ.json
```

**TileJSON:**
```
https://d30uc1nx5aa6eq.cloudfront.net/stac/tilejson.json?url=https%3A%2F%2Fd30uc1nx5aa6eq.cloudfront.net%2Fjobs%2F01K55BB201KNAM8C3N9SF8TMEJ%2Fstac%2Fitems%2F01K55BB202VWS3XH5MPA0Z73WZ.json&assets=analysis&format=webp
```

**XYZ Tile:**
```
https://d30uc1nx5aa6eq.cloudfront.net/stac/tiles/10/902/637.webp?url=https%3A%2F%2Fd30uc1nx5aa6eq.cloudfront.net%2Fjobs%2F01K55BB201KNAM8C3N9SF8TMEJ%2Fstac%2Fitems%2F01K55BB202VWS3XH5MPA0Z73WZ.json&assets=analysis
```

---

### **🔐 Headers & Authentication**

- **Browser → CloudFront**: Normal GETs with CORS for web map domain
- **CloudFront → S3 (OAC)**: Bucket policy allows only CloudFront OAC principal
- **CloudFront → TiTiler**: Forward full query string (critical for cache keys)
- **TiTiler → S3 COGs**: Lambda IAM role grants `s3:GetObject` + `s3:ListBucket`

**IAM Policy (Configuration-Driven):**
```json
{
  "Statement": [
    {
      "Sid": "ReadCOGs",
      "Effect": "Allow", 
      "Action": ["s3:GetObject"],
      "Resource": "arn:aws:s3:::geoexhibit-demo/jobs/*"
    },
    {
      "Sid": "ListBucket",
      "Effect": "Allow",
      "Action": ["s3:ListBucket"], 
      "Resource": "arn:aws:s3:::geoexhibit-demo"
    }
  ]
}
```

---

### **⚡ Caching Strategy (CloudFront)**

- **Static assets** (HTML/JS): Long TTL (7 days), version on deploy
- **STAC data** (Collection/Items): Medium TTL (1 day), immutable per job
- **PMTiles**: Long TTL (7 days), immutable vector data
- **TileJSON**: Short TTL (1-5 minutes), cache by full query string
- **Tiles**: Medium TTL (10-60 minutes), vary by path + query parameters

---

### **🐛 Error Handling Quick Reference**

- **403 on COG fetch**: Check Lambda IAM role has `s3:GetObject` on COG paths
- **CORS blocked**: Ensure `Access-Control-Allow-Origin` on both S3 and TiTiler responses
- **TileJSON 4xx**: Verify Item URL format and asset names match STAC schema
- **Collection not found**: Check CloudFront routing for `/jobs/*/stac/*` pattern
- **PMTiles not loading**: Verify CloudFront routing for `/jobs/*/pmtiles/*.pmtiles`

---

### **🧪 Steel Thread Testing**

**Web Map URL:**
```
http://localhost:8000/?cloudfront=https://d30uc1nx5aa6eq.cloudfront.net&job_id=01K55BB201KNAM8C3N9SF8TMEJ
```

**Validation Script:**
```bash
python3 steel_thread_test.py https://d30uc1nx5aa6eq.cloudfront.net
```

**Expected Flow:**
1. ✅ Web map loads with South Australia view
2. ✅ PMTiles displays 3 fire polygons
3. ✅ Click fire area → STAC Item loads via CloudFront
4. ✅ TiTiler returns TileJSON with tile template
5. ✅ Leaflet displays raster overlay from TiTiler tiles

