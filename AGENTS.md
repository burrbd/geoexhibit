
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

## 🧪 **Testing Strategy**

- **Unit tests**: Each component tested in isolation with mocks
- **Integration tests**: End-to-end workflow with LocalPublisher (no AWS)
- **S3 mocking**: boto3 stubber for S3Publisher tests
- **CLI testing**: Click TestRunner for command validation
- **Coverage**: 85%+ on core modules, skip heavy dependency modules in CI

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

Rules are stored in .cursor/rules for Cursor registration.

