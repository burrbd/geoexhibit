#!/usr/bin/env python3
"""
Steel Thread Lambda handler for infrastructure testing.
Provides basic TiTiler-compatible endpoints for steel thread validation.
"""

import json
import os
import urllib.parse
from typing import Dict, Any


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Steel thread Lambda handler for infrastructure testing."""
    
    # Parse the request
    http_method = event.get('requestContext', {}).get('http', {}).get('method', 'GET')
    path = event.get('rawPath', event.get('path', '/'))
    query_params = event.get('queryStringParameters') or {}
    
    print(f"Request: {http_method} {path} - Query: {query_params}")
    
    # CORS headers for all responses
    cors_headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, HEAD, OPTIONS',
        'Access-Control-Allow-Headers': '*',
        'Access-Control-Expose-Headers': 'Content-Length, Content-Type, ETag'
    }
    
    # Health endpoint
    if path == '/health':
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                **cors_headers
            },
            'body': json.dumps({
                'status': 'healthy',
                'service': 'geoexhibit-steel-thread',
                'message': 'Steel thread infrastructure deployed and functional',
                'bucket': os.environ.get('S3_BUCKET', 'geoexhibit-demo')
            })
        }
    
    # STAC info endpoint (basic implementation)
    if path.startswith('/stac/info'):
        stac_url = query_params.get('url', '')
        if not stac_url:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json', **cors_headers},
                'body': json.dumps({'detail': 'Missing required parameter: url'})
            }
        
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json', **cors_headers},
            'body': json.dumps({
                'steel_thread_note': 'Basic STAC info endpoint for infrastructure testing',
                'input_url': stac_url,
                'bounds': [138.6, -35.1, 138.9, -34.9],  # South Australia bounds
                'dtype': 'uint16',
                'minzoom': 5,
                'maxzoom': 14,
                'message': 'For full TiTiler functionality, deploy proper TiTiler package'
            })
        }
    
    # STAC TileJSON endpoint (basic implementation)
    if path.startswith('/stac/tilejson.json'):
        stac_url = query_params.get('url', '')
        assets = query_params.get('assets', 'analysis')
        
        if not stac_url:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json', **cors_headers},
                'body': json.dumps({'detail': 'Missing required parameter: url'})
            }
        
        # Get the CloudFront domain from the request
        host = event.get('headers', {}).get('host', 'localhost')
        
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json', **cors_headers},
            'body': json.dumps({
                'tilejson': '2.2.0',
                'name': assets,
                'minzoom': 5,
                'maxzoom': 14,
                'bounds': [138.6, -35.1, 138.9, -34.9],
                'tiles': [
                    f"https://{host}/stac/tiles/{{z}}/{{x}}/{{y}}.png?url={urllib.parse.quote(stac_url)}&assets={assets}"
                ],
                'steel_thread_note': 'Basic TileJSON for infrastructure testing - deploy full TiTiler for real tiles'
            })
        }
    
    # STAC tiles endpoint (returns placeholder)
    if path.startswith('/stac/tiles/'):
        # Extract z/x/y from path like /stac/tiles/10/902/637.png
        path_parts = path.split('/')
        if len(path_parts) >= 6:
            z, x, y_file = path_parts[3], path_parts[4], path_parts[5]
            y = y_file.split('.')[0]  # Remove extension
            
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'image/png',
                    **cors_headers
                },
                'body': 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChAI9dJxebAAAAABJRU5ErkJggg==',  # 1x1 transparent PNG
                'isBase64Encoded': True
            }
    
    # Default response
    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json', **cors_headers},
        'body': json.dumps({
            'message': 'Steel thread infrastructure endpoint',
            'path': path,
            'method': http_method,
            'available_endpoints': ['/health', '/stac/info', '/stac/tilejson.json', '/stac/tiles/{z}/{x}/{y}'],
            'note': 'Basic endpoints for steel thread testing - deploy full TiTiler for production'
        })
    }