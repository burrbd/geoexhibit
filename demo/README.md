# GeoExhibit Demo Files

This directory contains all demo-related files for GeoExhibit, including sample data, configuration, and verification scripts.

## Files

### Core Demo Data
- **`features.json`** - Sample fire analysis features (3 polygons/points in South Australia)
- **`config.json`** - Complete demo configuration for fire analysis workflow

### Testing & Verification
- **`steel_thread_test.py`** - End-to-end infrastructure validation script
- **`verify_aws_publishing.py`** - AWS API verification for published STAC data
- **`test_demo.py`** - Automated demo workflow testing

## Usage

### Quick Demo Run
```bash
# From project root
geoexhibit run demo/config.json

# Local testing
geoexhibit run demo/config.json --local-out ./demo_output
```

### Verify Published Data
```bash
# After publishing, verify structure
python demo/verify_aws_publishing.py demo/config.json <job_id>
```

### Steel Thread Testing
```bash
# Test complete infrastructure (requires deployed CloudFront)
python demo/steel_thread_test.py https://YOUR_CLOUDFRONT_URL
```

## Demo Data Details

The **features.json** contains 3 sample fire areas:
- **Fire Area A** (Sept 15, 2023) - High severity polygon
- **Fire Area B** (Oct 2, 2023) - Moderate severity polygon  
- **Fire Point** (Nov 20, 2023) - Low severity point

Each feature includes:
- `fire_date` - Used for temporal analysis
- `severity` - Demo categorization
- `area_hectares` - Area metadata

## Expected Output

Demo run produces:
```
s3://geoexhibit-demo/jobs/<job_id>/
├── stac/
│   ├── collection.json
│   └── items/
│       ├── <item1>.json
│       ├── <item2>.json
│       └── <item3>.json
├── assets/
│   ├── <item1>/analysis.tif
│   ├── <item2>/analysis.tif
│   └── <item3>/analysis.tif
└── pmtiles/
    └── features.pmtiles
```

All demo COGs are synthetic but properly structured Cloud Optimized GeoTIFFs with TiTiler-compatible metadata.