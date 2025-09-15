#!/usr/bin/env python3
"""
Simple steel thread test that mimics the web map sequence.
Tests the exact same flow as described in AGENTS.md steel thread documentation.
"""

import json
import sys
import urllib.parse
from pathlib import Path
from typing import Optional

import requests


def test_steel_thread_sequence(cloudfront_url: str, job_id: str) -> bool:
    """
    Test the exact sequence that the web map follows.
    Mimics the steel thread flow documented in AGENTS.md.
    """
    print("🎯 Steel Thread End-to-End Test")
    print("=" * 60)
    print(f"CloudFront URL: {cloudfront_url}")
    print(f"Job ID: {job_id}")
    print("")
    
    # Step 1: Load Collection (entry point)
    print("1️⃣ Loading STAC Collection (entry point)...")
    collection_url = f"{cloudfront_url}/jobs/{job_id}/stac/collection.json"
    
    try:
        response = requests.get(collection_url, timeout=10)
        if response.status_code == 200:
            collection = response.json()
            print(f"   ✅ Collection loaded: {collection.get('id')}")
            
            # Find PMTiles link
            pmtiles_links = [link for link in collection.get('links', []) if link.get('rel') == 'pmtiles']
            if pmtiles_links:
                pmtiles_href = pmtiles_links[0].get('href', '')
                print(f"   ✅ PMTiles link found: {pmtiles_href}")
            else:
                print("   ⚠️  No PMTiles link in collection")
        else:
            print(f"   ❌ Collection failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Collection error: {e}")
        return False
    
    # Step 2: Load PMTiles (vector overlay)
    print("\n2️⃣ Loading PMTiles vector layer...")
    pmtiles_url = f"{cloudfront_url}/jobs/{job_id}/pmtiles/features.pmtiles"
    
    try:
        response = requests.head(pmtiles_url, timeout=10)
        if response.status_code == 200:
            size = response.headers.get('content-length', 'unknown')
            print(f"   ✅ PMTiles accessible: {size} bytes")
        else:
            print(f"   ❌ PMTiles failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ PMTiles error: {e}")
        return False
    
    # Step 3: Load STAC Item (feature click simulation)
    print("\n3️⃣ Loading STAC Item (simulating feature click)...")
    
    # Get first item from collection links or compute item path
    item_links = [link for link in collection.get('links', []) if link.get('rel') == 'item']
    if item_links:
        item_href = item_links[0].get('href', '')
        # Resolve relative href
        if item_href.startswith('../'):
            item_url = f"{cloudfront_url}/jobs/{job_id}/stac/{item_href[3:]}"
        else:
            item_url = f"{cloudfront_url}/jobs/{job_id}/stac/{item_href}"
    else:
        # Fallback: try to find an item by listing
        print("   📋 No item links in collection, checking S3...")
        try:
            import boto3
            s3 = boto3.client('s3', region_name='ap-southeast-2')
            items_prefix = f"jobs/{job_id}/stac/items/"
            
            response = s3.list_objects_v2(Bucket='geoexhibit-demo', Prefix=items_prefix, MaxKeys=1)
            if 'Contents' in response:
                first_item_key = response['Contents'][0]['Key']
                item_url = f"{cloudfront_url}/{first_item_key}"
            else:
                print("   ❌ No STAC items found")
                return False
        except Exception as e:
            print(f"   ❌ Failed to find STAC item: {e}")
            return False
    
    try:
        response = requests.get(item_url, timeout=10)
        if response.status_code == 200:
            item = response.json()
            print(f"   ✅ STAC Item loaded: {item.get('id')}")
            
            # Find primary asset for TiTiler
            assets = item.get('assets', {})
            primary_assets = [
                (name, asset) for name, asset in assets.items()
                if isinstance(asset.get('roles'), list) and 'primary' in asset['roles']
            ]
            
            if primary_assets:
                asset_name, primary_asset = primary_assets[0]
                cog_href = primary_asset.get('href', '')
                print(f"   ✅ Primary COG asset: {asset_name} -> {cog_href}")
            else:
                print("   ❌ No primary COG asset found")
                return False
        else:
            print(f"   ❌ STAC Item failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ STAC Item error: {e}")
        return False
    
    # Step 4: Request TileJSON from TiTiler (raster integration)
    print("\n4️⃣ Requesting TileJSON from TiTiler...")
    encoded_item_url = urllib.parse.quote(item_url, safe="")
    tilejson_url = f"{cloudfront_url}/stac/tilejson.json?url={encoded_item_url}&assets={asset_name}&format=webp"
    
    try:
        response = requests.get(tilejson_url, timeout=20)
        if response.status_code == 200:
            tilejson = response.json()
            required_fields = ['tilejson', 'tiles', 'bounds']
            
            if all(field in tilejson for field in required_fields):
                print(f"   ✅ TileJSON generated successfully")
                print(f"   📐 Bounds: {tilejson['bounds']}")
                
                tiles_template = tilejson['tiles'][0] if tilejson['tiles'] else None
                if tiles_template:
                    print(f"   🗺️  Tiles template: {tiles_template}")
                else:
                    print("   ❌ No tiles template in TileJSON")
                    return False
            else:
                missing = [f for f in required_fields if f not in tilejson]
                print(f"   ❌ TileJSON missing fields: {missing}")
                return False
        else:
            print(f"   ❌ TileJSON failed: {response.status_code}")
            if response.text:
                print(f"      Response: {response.text[:200]}")
            return False
    except Exception as e:
        print(f"   ❌ TileJSON error: {e}")
        return False
    
    # Step 5: Request sample tile (final validation)
    print("\n5️⃣ Requesting sample raster tile...")
    # Extract tile template and make a sample request
    tile_template = tilejson['tiles'][0]
    sample_tile_url = tile_template.format(z=8, x=240, y=160)  # Mid-zoom for South Australia
    
    try:
        response = requests.get(sample_tile_url, timeout=20)
        if response.status_code == 200:
            content_type = response.headers.get('content-type', '')
            if 'image' in content_type:
                print(f"   ✅ Raster tile generated: {content_type}, {len(response.content)} bytes")
            else:
                print(f"   ❌ Invalid tile content type: {content_type}")
                return False
        else:
            print(f"   ❌ Tile request failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Tile request error: {e}")
        return False
    
    # Success!
    print("\n🎉 STEEL THREAD END-TO-END TEST: PASSED")
    print("=" * 60)
    print("✅ Complete web map sequence validated:")
    print("   1. Collection JSON loaded via CloudFront → S3")
    print("   2. PMTiles accessible for vector overlay")
    print("   3. STAC Item loaded via CloudFront → S3")
    print("   4. TiTiler TileJSON generated successfully")
    print("   5. Raster tiles rendered and accessible")
    print("")
    print("🌐 Ready for web map testing:")
    print(f"   http://localhost:8000/?cloudfront={cloudfront_url}&job_id={job_id}")
    
    return True


def main():
    """Main test function."""
    if len(sys.argv) != 3:
        print("Usage: python3 steel_thread_test.py <cloudfront_url> <job_id>")
        print("Example: python3 steel_thread_test.py https://d123.cloudfront.net 01K55BB201KNAM8C3N9SF8TMEJ")
        sys.exit(1)
    
    cloudfront_url = sys.argv[1].rstrip("/")
    job_id = sys.argv[2]
    
    success = test_steel_thread_sequence(cloudfront_url, job_id)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()