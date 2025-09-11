"""STAC writing functionality with strict HREF rules enforcement."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
import pystac
from pystac.extensions.projection import ProjectionExtension
from pystac.extensions.raster import RasterExtension
from pystac.extensions.processing import ProcessingExtension
from shapely.geometry import shape
from ulid import ULID

from .interfaces import PublishPlan, PublishItem, AssetSpec, TimeSpan, GeoExhibitConfig

logger = logging.getLogger(__name__)


class HrefResolver:
    """
    Enforces GeoExhibit HREF rules:
    - COG assets: fully qualified S3 URLs (s3://bucket/key.tif)
    - All other HREFs: strictly relative paths
    """
    
    def __init__(self, config: GeoExhibitConfig, job_id: str):
        """Initialize with configuration and job ID."""
        self.config = config
        self.job_id = job_id
        self.s3_bucket = config.s3_bucket
    
    def resolve_asset_href(self, asset: AssetSpec, is_cog: bool = False) -> str:
        """
        Resolve asset HREF according to GeoExhibit rules.
        
        Args:
            asset: AssetSpec with relative href
            is_cog: True if this is a COG asset (gets S3 URL)
            
        Returns:
            Resolved HREF string
        """
        if is_cog:
            # COG assets get fully qualified S3 URLs
            if asset.href.startswith('s3://'):
                return asset.href  # Already qualified
            else:
                # Build S3 URL with job scoping
                jobs_prefix = self.config.get_s3_prefix("jobs")
                s3_key = f"{jobs_prefix}{self.job_id}/{asset.href}"
                return f"s3://{self.s3_bucket}/{s3_key}"
        else:
            # All other assets get relative paths (job-scoped)
            if asset.href.startswith('/') or '://' in asset.href:
                raise ValueError(f"Non-COG asset HREF must be relative: {asset.href}")
            return f"jobs/{self.job_id}/{asset.href}"
    
    def resolve_stac_href(self, relative_path: str, stac_type: str) -> str:
        """
        Resolve STAC JSON file HREF (always relative).
        
        Args:
            relative_path: Relative path for the STAC file
            stac_type: Type of STAC file ('collection', 'item', etc.)
            
        Returns:
            Relative HREF path with job scoping
        """
        if relative_path.startswith('/') or '://' in relative_path:
            raise ValueError(f"STAC HREF must be relative: {relative_path}")
        
        # STAC files are scoped under jobs/<job_id>/stac/...
        return f"jobs/{self.job_id}/stac/{stac_type}s/{relative_path}"
    
    def resolve_pmtiles_href(self, relative_path: str) -> str:
        """Resolve PMTiles HREF (always relative, job-scoped)."""
        if relative_path.startswith('/') or '://' in relative_path:
            raise ValueError(f"PMTiles HREF must be relative: {relative_path}")
        
        return f"jobs/{self.job_id}/pmtiles/{relative_path}"


def create_stac_collection(plan: PublishPlan, config: GeoExhibitConfig, 
                          href_resolver: HrefResolver) -> pystac.Collection:
    """
    Create a STAC Collection from the publish plan.
    
    Args:
        plan: PublishPlan with items and metadata
        config: GeoExhibit configuration
        href_resolver: HREF resolver for this job
        
    Returns:
        STAC Collection with proper links and extensions
    """
    # Calculate temporal extent from all items
    start_times = []
    end_times = []
    
    for item in plan.items:
        timespan = item.timespan
        start_times.append(timespan.start)
        if timespan.end:
            end_times.append(timespan.end)
        else:
            end_times.append(timespan.start)
    
    temporal_extent = pystac.TemporalExtent([[min(start_times), max(end_times)]])
    
    # Calculate spatial extent from all items
    all_geometries = [shape(item.geometry) for item in plan.items]
    
    # Get bounding box that encompasses all geometries
    min_x = min(geom.bounds[0] for geom in all_geometries)
    min_y = min(geom.bounds[1] for geom in all_geometries)
    max_x = min(geom.bounds[2] for geom in all_geometries)
    max_y = max(geom.bounds[3] for geom in all_geometries)
    
    spatial_extent = pystac.SpatialExtent([[min_x, min_y, max_x, max_y]])
    extent = pystac.Extent(spatial=spatial_extent, temporal=temporal_extent)
    
    # Create collection
    collection_metadata = plan.collection_metadata
    collection = pystac.Collection(
        id=plan.collection_id,
        description=collection_metadata.get("description", "GeoExhibit Collection"),
        extent=extent,
        title=collection_metadata.get("title"),
        keywords=collection_metadata.get("keywords", []),
        license=collection_metadata.get("license", "proprietary"),
        providers=collection_metadata.get("providers", []),
        extra_fields=collection_metadata.get("extra_fields", {})
    )
    
    # Add extensions
    for ext_name in config.use_extensions:
        if ext_name == "proj":
            ProjectionExtension.add_to(collection)
        elif ext_name == "raster":
            RasterExtension.add_to(collection)
        elif ext_name == "processing":
            ProcessingExtension.add_to(collection)
    
    # Add PMTiles link if available
    if plan.pmtiles_path:
        pmtiles_href = href_resolver.resolve_pmtiles_href(plan.pmtiles_path)
        pmtiles_link = pystac.Link(
            rel="pmtiles",
            target=pmtiles_href,
            media_type="application/x-pmtiles",
            title="Vector tiles (PMTiles)"
        )
        collection.add_link(pmtiles_link)
    
    return collection


def create_stac_item(publish_item: PublishItem, collection: pystac.Collection, 
                    config: GeoExhibitConfig, href_resolver: HrefResolver) -> pystac.Item:
    """
    Create a STAC Item from a PublishItem.
    
    Args:
        publish_item: PublishItem with feature and analyzer output
        collection: Parent collection
        config: GeoExhibit configuration
        href_resolver: HREF resolver for this job
        
    Returns:
        STAC Item with proper assets and extensions
    """
    # Get geometry and bbox
    geometry = publish_item.geometry
    geom_shape = shape(geometry)
    bbox = list(geom_shape.bounds)
    
    # Set up datetime
    timespan = publish_item.timespan
    if timespan.is_instant:
        datetime_val = timespan.start
        start_datetime = None
        end_datetime = None
    else:
        datetime_val = None
        start_datetime = timespan.start
        end_datetime = timespan.end
    
    # Create the item
    item = pystac.Item(
        id=publish_item.item_id,
        geometry=geometry if config.stac.get("geometry_in_item", True) else None,
        bbox=bbox,
        datetime=datetime_val,
        properties=publish_item.properties,
        collection=collection.id
    )
    
    # Set start/end datetime if not instant
    if not timespan.is_instant:
        item.common_metadata.start_datetime = start_datetime
        item.common_metadata.end_datetime = end_datetime
    
    # Add extensions
    for ext_name in config.use_extensions:
        if ext_name == "proj":
            proj_ext = ProjectionExtension.ext(item)
            # Set EPSG:4326 as the projection
            proj_ext.epsg = 4326
        elif ext_name == "raster":
            RasterExtension.add_to(item)
        elif ext_name == "processing":
            ProcessingExtension.add_to(item)
    
    # Add assets
    analyzer_output = publish_item.analyzer_output
    
    # Add primary COG asset with required roles
    primary_asset = analyzer_output.primary_cog_asset
    primary_href = href_resolver.resolve_asset_href(primary_asset, is_cog=True)
    
    # Ensure primary COG has required roles
    primary_roles = list(primary_asset.roles or [])
    if "data" not in primary_roles:
        primary_roles.append("data")
    if "primary" not in primary_roles:
        primary_roles.append("primary")
    
    pystac_asset = pystac.Asset(
        href=primary_href,
        title=primary_asset.title,
        description=primary_asset.description,
        media_type=primary_asset.media_type or "image/tiff; application=geotiff; profile=cloud-optimized",
        roles=primary_roles,
        extra_fields=primary_asset.extra_fields or {}
    )
    
    item.add_asset(primary_asset.key, pystac_asset)
    
    # Add additional assets
    if analyzer_output.additional_assets:
        for asset_spec in analyzer_output.additional_assets:
            asset_href = href_resolver.resolve_asset_href(asset_spec, is_cog=False)
            
            additional_asset = pystac.Asset(
                href=asset_href,
                title=asset_spec.title,
                description=asset_spec.description,
                media_type=asset_spec.media_type,
                roles=asset_spec.roles,
                extra_fields=asset_spec.extra_fields or {}
            )
            
            item.add_asset(asset_spec.key, additional_asset)
    
    return item


def write_stac_catalog(plan: PublishPlan, config: GeoExhibitConfig, 
                      output_dir: Optional[Path] = None) -> Dict[str, Any]:
    """
    Write complete STAC catalog for the publish plan.
    
    Args:
        plan: PublishPlan to write
        config: GeoExhibit configuration  
        output_dir: Optional local output directory (for --local-out mode)
        
    Returns:
        Dictionary with paths and metadata for the written STAC files
    """
    href_resolver = HrefResolver(config, plan.job_id)
    
    # Create collection
    collection = create_stac_collection(plan, config, href_resolver)
    
    # Create items
    items = []
    for publish_item in plan.items:
        item = create_stac_item(publish_item, collection, config, href_resolver)
        items.append(item)
        collection.add_item(item)
    
    # Prepare output paths
    if output_dir:
        # Local output mode
        stac_dir = output_dir / "stac"
        collections_dir = stac_dir / "collections"
        items_dir = stac_dir / "items"
        
        collections_dir.mkdir(parents=True, exist_ok=True)
        items_dir.mkdir(parents=True, exist_ok=True)
        
        collection_path = collections_dir / f"{plan.collection_id}.json"
        item_paths = []
        
        for item in items:
            item_path = items_dir / f"{item.id}.json"
            item_paths.append(item_path)
    
    else:
        # S3 output mode - return relative paths that will be resolved later
        collection_path = href_resolver.resolve_stac_href(f"{plan.collection_id}.json", "collection")
        item_paths = [
            href_resolver.resolve_stac_href(f"{item.id}.json", "item") 
            for item in items
        ]
    
    # Validate STAC before writing/returning
    _validate_stac_collection(collection)
    for item in items:
        _validate_stac_item(item, config)
    
    logger.info(f"Generated STAC catalog with {len(items)} items")
    
    return {
        "collection": {
            "path": str(collection_path),
            "object": collection
        },
        "items": [
            {
                "path": str(path),
                "object": item
            }
            for path, item in zip(item_paths, items)
        ],
        "job_id": plan.job_id,
        "collection_id": plan.collection_id
    }


def _validate_stac_collection(collection: pystac.Collection) -> None:
    """Validate STAC Collection."""
    try:
        collection.validate()
        logger.debug(f"STAC Collection {collection.id} is valid")
    except Exception as e:
        raise ValueError(f"Invalid STAC Collection: {e}")


def _validate_stac_item(item: pystac.Item, config: GeoExhibitConfig) -> None:
    """Validate STAC Item and check for primary COG asset."""
    try:
        item.validate()
        logger.debug(f"STAC Item {item.id} is valid")
        
        # Check for primary COG asset
        primary_assets = [
            asset for asset in item.assets.values()
            if asset.roles and "primary" in asset.roles and "data" in asset.roles
        ]
        
        if not primary_assets:
            raise ValueError(f"STAC Item {item.id} missing primary COG asset with 'data' and 'primary' roles")
        
        if len(primary_assets) > 1:
            logger.warning(f"STAC Item {item.id} has multiple primary assets")
        
        # Validate primary asset HREF is fully qualified S3 URL
        primary_asset = primary_assets[0]
        if not primary_asset.href.startswith("s3://"):
            raise ValueError(f"Primary COG asset HREF must be fully qualified S3 URL: {primary_asset.href}")
        
        logger.debug(f"STAC Item {item.id} has valid primary COG asset")
        
    except Exception as e:
        raise ValueError(f"Invalid STAC Item {item.id}: {e}")