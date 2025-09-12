#!/usr/bin/env python3
"""
AWS Lambda handler for TiTiler.
"""

import logging

from mangum import Mangum

from titiler.application.main import app

logging.getLogger("mangum.lifespan").setLevel(logging.ERROR)
logging.getLogger("mangum.http").setLevel(logging.ERROR)

# Add custom health endpoint
@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "healthy", "service": "geoexhibit"}

handler = Mangum(app, lifespan="auto")
