#!/usr/bin/env python3
"""
Infrastructure validation script for GeoExhibit.
Tests deployed TiTiler endpoints with existing demo data.
"""

import json
import sys
import urllib.parse
from typing import Dict, Any

import requests


def validate_health_endpoint(cloudfront_url: str) -> bool:
    """Validate health endpoint responds correctly."""
    try:
        response = requests.get(f"{cloudfront_url}/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "healthy" and data.get("service") == "geoexhibit":
                print("✅ Health endpoint: OK")
                return True
        print(f"❌ Health endpoint: Failed - {response.status_code}")
        return False
    except Exception as e:
        print(f"❌ Health endpoint: Error - {e}")
        return False


def validate_stac_tilejson(cloudfront_url: str, stac_item_url: str) -> bool:
    """Validate TileJSON endpoint works with STAC item."""
    encoded_url = urllib.parse.quote(stac_item_url, safe="")
    tilejson_url = f"{cloudfront_url}/stac/tilejson.json?url={encoded_url}&format=webp"
    
    try:
        response = requests.get(tilejson_url, timeout=15)
        if response.status_code == 200:
            data = response.json()
            required_fields = ["tilejson", "tiles", "bounds"]
            if all(field in data for field in required_fields):
                print("✅ STAC TileJSON: OK")
                print(f"   Bounds: {data['bounds']}")
                print(f"   Tiles template: {data['tiles'][0] if data['tiles'] else 'None'}")
                return True
        print(f"❌ STAC TileJSON: Failed - {response.status_code}")
        if response.status_code != 200:
            print(f"   Response: {response.text[:200]}...")
        return False
    except Exception as e:
        print(f"❌ STAC TileJSON: Error - {e}")
        return False


def validate_tile_request(cloudfront_url: str, stac_item_url: str) -> bool:
    """Validate actual tile request works."""
    encoded_url = urllib.parse.quote(stac_item_url, safe="")
    # Test a middle zoom level tile (likely to contain data)
    tile_url = f"{cloudfront_url}/stac/tiles/8/128/128.png?url={encoded_url}&format=webp"
    
    try:
        response = requests.get(tile_url, timeout=15)
        if response.status_code == 200:
            content_type = response.headers.get('content-type', '')
            if 'image' in content_type:
                print("✅ Tile request: OK")
                print(f"   Content-Type: {content_type}")
                print(f"   Size: {len(response.content)} bytes")
                return True
        print(f"❌ Tile request: Failed - {response.status_code}")
        return False
    except Exception as e:
        print(f"❌ Tile request: Error - {e}")
        return False


def validate_cors(cloudfront_url: str) -> bool:
    """Validate CORS headers are present."""
    try:
        response = requests.options(f"{cloudfront_url}/health", timeout=10)
        cors_origin = response.headers.get('access-control-allow-origin')
        if cors_origin:
            print(f"✅ CORS: OK - Origin: {cors_origin}")
            return True
        else:
            print("❌ CORS: Missing access-control-allow-origin header")
            return False
    except Exception as e:
        print(f"❌ CORS: Error - {e}")
        return False


def main():
    """Main validation function."""
    if len(sys.argv) != 2:
        print("Usage: python validate-infrastructure.py <cloudfront_url>")
        print("Example: python validate-infrastructure.py https://d1234567890.cloudfront.net")
        sys.exit(1)
    
    cloudfront_url = sys.argv[1].rstrip('/')
    
    print("🔍 GeoExhibit Infrastructure Validation")
    print(f"CloudFront URL: {cloudfront_url}")
    print("")
    
    # Use existing demo STAC item for validation
    demo_stac_item = "https://geoexhibit-demo.s3.ap-southeast-2.amazonaws.com/jobs/01K4XRE3K3KQDMTZ60XY1XWMN4/stac/items/01K4XRE3KB6H2JPVKHE77YE7QA.json"
    
    print(f"Testing with demo STAC item: {demo_stac_item}")
    print("")
    
    # Run all validations
    results = []
    results.append(validate_health_endpoint(cloudfront_url))
    results.append(validate_cors(cloudfront_url))
    results.append(validate_stac_tilejson(cloudfront_url, demo_stac_item))
    results.append(validate_tile_request(cloudfront_url, demo_stac_item))
    
    print("")
    print("=" * 50)
    
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"🎉 All validations passed! ({passed}/{total})")
        print("")
        print("Steel-thread validation complete:")
        print("✅ TiTiler Lambda deployed with GDAL/COG support")
        print("✅ CloudFront distribution serving tiles")
        print("✅ CORS enabled for web map access")
        print("✅ Health checks responding correctly")
        sys.exit(0)
    else:
        print(f"❌ {total - passed} validations failed ({passed}/{total})")
        print("")
        print("Check the error messages above and redeploy if necessary.")
        sys.exit(1)


if __name__ == "__main__":
    main()