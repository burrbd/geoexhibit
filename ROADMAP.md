# GeoExhibit Development Roadmap

## 🎯 **Current Status: Foundation Complete**

All 8 main acceptance criteria achieved with working demo dataset published to S3 and verified via AWS APIs.

**Demo Dataset**: `s3://geoexhibit-demo/jobs/01K4XRE3K3KQDMTZ60XY1XWMN4/`  
**Verification**: 5/5 checks passed (Collection + Items + COGs + PMTiles + TiTiler compatible)

## 🚀 **Next Development Phases**

GitHub issues created for continued development following the steel-thread approach:

### **Phase 1: Infrastructure Steel Thread**
- **[Issue #2](https://github.com/burrbd/geoexhibit/issues/2)**: 🏗️ Terraform Infrastructure 
- **[Issue #3](https://github.com/burrbd/geoexhibit/issues/3)**: ✅ Steel-Thread Verification

**Goal**: Deploy TiTiler + CloudFront infrastructure and validate end-to-end web map functionality.

### **Phase 2: Plugin System**  
- **[Issue #4](https://github.com/burrbd/geoexhibit/issues/4)**: 🔌 Plugin Architecture

**Goal**: Enable custom analyzer development with simple `@register()` decorator system.

### **Phase 3: Enhanced Web Experience**
- **[Issue #5](https://github.com/burrbd/geoexhibit/issues/5)**: 🗺️ Basic Web Map 
- **[Issue #6](https://github.com/burrbd/geoexhibit/issues/6)**: 🗺️ TiTiler Integration + Time Slider

**Goal**: Complete interactive web map with feature selection and temporal raster display.

### **Phase 4: Production Analysis**
- **[Issue #7](https://github.com/burrbd/geoexhibit/issues/7)**: 🔬 Real-World Analyzer (dNBR via Google Earth Engine)
- **[Issue #9](https://github.com/burrbd/geoexhibit/issues/9)**: 🛠️ COG Helper Functions

**Goal**: Production-ready fire severity analysis with Google Earth Engine integration.

### **Phase 5: Scale & Performance**
- **[Issue #8](https://github.com/burrbd/geoexhibit/issues/8)**: ⚡ Performance Optimizations

**Goal**: Scale to 100+ features with parallel processing and memory management.

## 📋 **Dependency Chain**

```
Infrastructure (1a) → Steel-Thread (1b) → Enhanced Web Map (3a, 3b)
Plugin Architecture (2) → Real-World Analyzer (4) → Performance (5)
COG Helpers (supporting) ← can support Real-World Analyzer
```

## 🎯 **User Journey After Completion**

1. **Install GeoExhibit**: `pip install geoexhibit`
2. **Write Custom Analyzer**: 
   ```python
   @analyzer.register("my_analysis")
   class MyAnalyzer:
       def analyze(self, feature, timespan):
           # Custom analysis logic
           return AnalyzerOutput(...)
   ```
3. **Configure and Run**: 
   ```json
   {"analyzer": "my_analysis", ...}
   ```
   ```bash
   geoexhibit run config.json
   ```
4. **Deploy Infrastructure**: `terraform apply`
5. **View Results**: Open web map → see features + raster analyses

## 📊 **Success Metrics**

- **Infrastructure**: TiTiler serves demo COGs correctly
- **Plugin System**: 3rd party can write analyzer in <20 lines of code
- **Web Map**: Click feature → see raster in <3 seconds  
- **Real-World**: Process actual fire data with GEE → publish working dNBR
- **Performance**: Handle 100+ features with reasonable resources

Each phase builds on proven functionality, ensuring the steel thread remains intact throughout development.