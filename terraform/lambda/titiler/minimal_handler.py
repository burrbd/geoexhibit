#!/usr/bin/env python3
"""
Minimal Lambda handler for steel thread testing.
Provides basic endpoints to enable CloudFront deployment.
"""

import json


def handler(event, context):
    """Minimal Lambda handler for steel thread infrastructure testing."""
    
    # Parse the request
    http_method = event.get('httpMethod', event.get('requestContext', {}).get('http', {}).get('method', 'GET'))
    path = event.get('path', event.get('rawPath', '/'))
    
    # Health endpoint
    if path == '/health':
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, HEAD, OPTIONS',
                'Access-Control-Allow-Headers': '*'
            },
            'body': json.dumps({
                'status': 'healthy',
                'service': 'geoexhibit-minimal',
                'message': 'Basic steel thread infrastructure deployed'
            })
        }
    
    # Basic response for all other endpoints
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, HEAD, OPTIONS',
            'Access-Control-Allow-Headers': '*'
        },
        'body': json.dumps({
            'message': 'Steel thread infrastructure endpoint',
            'path': path,
            'method': http_method,
            'note': 'Full TiTiler functionality requires proper package build'
        })
    }