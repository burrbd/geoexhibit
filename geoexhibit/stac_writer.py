"""STAC writing functionality with strict HREF rules enforcement."""

import logging
from pathlib import Path
from typing import Dict, Any, Optional

import pystac
from pystac.extensions.projection import ProjectionExtension
from pystac.extensions.raster import RasterExtension
from shapely.geometry import shape

try:
    from pystac.extensions.processing import ProcessingExtension

    PROCESSING_EXTENSION_AVAILABLE = True
except ImportError:
    ProcessingExtension = None
    PROCESSING_EXTENSION_AVAILABLE = False

from .config import GeoExhibitConfig
from .layout import CanonicalLayout
from .publish_plan import PublishPlan, PublishItem

logger = logging.getLogger(__name__)


def _fix_item_link_hrefs(item_dict: dict) -> dict:
    """Fix item link hrefs to use proper relative paths instead of resolved absolute paths."""
    item_id = item_dict.get('id', '')
    for link in item_dict.get('links', []):
        if link.get('rel') == 'root' and link.get('href', '').endswith('/collection.json'):
            link['href'] = '../collection.json'
        elif link.get('rel') == 'collection' and link.get('href', '').endswith('/collection.json'):
            link['href'] = '../collection.json'
        elif link.get('rel') == 'self' and link.get('href', '').endswith(f'/{item_id}.json'):
            link['href'] = f'{item_id}.json'
    return item_dict


class HrefResolver:
    """
    Enforces GeoExhibit HREF rules using canonical layout:
    - COG assets: fully qualified S3 URLs (s3://bucket/jobs/<job_id>/assets/...)
    - All other HREFs: strictly relative paths within the canonical structure
    """

    def __init__(self, config: GeoExhibitConfig, layout: CanonicalLayout):
        """Initialize with configuration and canonical layout."""
        self.config = config
        self.layout = layout
        self.s3_bucket = config.s3_bucket

    def resolve_cog_asset_href(self, item_id: str, asset_name: str) -> str:
        """Resolve COG asset HREF to fully qualified S3 URL."""
        s3_key = self.layout.asset_path(item_id, asset_name)
        return f"s3://{self.s3_bucket}/{s3_key}"

    def resolve_thumbnail_href(self, item_id: str, thumb_name: str) -> str:
        """Resolve thumbnail HREF to relative path."""
        return f"../thumbs/{item_id}/{thumb_name}"

    def resolve_pmtiles_href(self) -> str:
        """Resolve PMTiles HREF (relative from collection perspective)."""
        return "../pmtiles/features.pmtiles"


def create_stac_collection(
    plan: PublishPlan, config: GeoExhibitConfig, layout: CanonicalLayout
) -> pystac.Collection:
    """Create a STAC Collection from the publish plan."""
    start_times = [item.timespan.start for item in plan.items]
    end_times = [
        item.timespan.end if item.timespan.end else item.timespan.start
        for item in plan.items
    ]

    temporal_extent = pystac.TemporalExtent([[min(start_times), max(end_times)]])

    all_geometries = [shape(item.geometry) for item in plan.items]

    min_x = min(geom.bounds[0] for geom in all_geometries)
    min_y = min(geom.bounds[1] for geom in all_geometries)
    max_x = max(geom.bounds[2] for geom in all_geometries)
    max_y = max(geom.bounds[3] for geom in all_geometries)

    spatial_extent = pystac.SpatialExtent([[min_x, min_y, max_x, max_y]])
    extent = pystac.Extent(spatial=spatial_extent, temporal=temporal_extent)

    collection_metadata = plan.collection_metadata
    collection = pystac.Collection(
        id=plan.collection_id,
        description=collection_metadata.get("description", "GeoExhibit Collection"),
        extent=extent,
        title=collection_metadata.get("title"),
        keywords=collection_metadata.get("keywords", []),
        license=collection_metadata.get("license", "proprietary"),
        providers=collection_metadata.get("providers", []),
        extra_fields=collection_metadata.get("extra_fields", {}),
    )

    for ext_name in config.use_extensions:
        if ext_name == "proj":
            ProjectionExtension.add_to(collection)
        elif ext_name == "raster":
            RasterExtension.add_to(collection)
        elif ext_name == "processing" and PROCESSING_EXTENSION_AVAILABLE:
            ProcessingExtension.add_to(collection)

    # Only add PMTiles link if PMTiles are included in the plan
    if hasattr(plan, "pmtiles_path") and plan.pmtiles_path:
        href_resolver = HrefResolver(config, layout)
        pmtiles_href = href_resolver.resolve_pmtiles_href()
        pmtiles_link = pystac.Link(
            rel="pmtiles",
            target=pmtiles_href,
            media_type="application/x-pmtiles",
            title="Vector tiles (PMTiles)",
        )
        collection.add_link(pmtiles_link)

    return collection


def create_stac_item(
    publish_item: PublishItem,
    collection: pystac.Collection,
    config: GeoExhibitConfig,
    layout: CanonicalLayout,
) -> pystac.Item:
    """Create a STAC Item from a PublishItem."""
    geometry = publish_item.geometry
    geom_shape = shape(geometry)
    bbox = list(geom_shape.bounds)

    timespan = publish_item.timespan
    if timespan.is_instant:
        datetime_val = timespan.start
        start_datetime = None
        end_datetime = None
    else:
        datetime_val = None
        start_datetime = timespan.start
        end_datetime = timespan.end

    item = pystac.Item(
        id=publish_item.item_id,
        geometry=geometry if config.stac.get("geometry_in_item", True) else None,
        bbox=bbox,
        datetime=datetime_val,
        properties=publish_item.properties,
        collection=collection.id,
    )

    if not timespan.is_instant:
        item.common_metadata.start_datetime = start_datetime
        item.common_metadata.end_datetime = end_datetime

    for ext_name in config.use_extensions:
        if ext_name == "proj":
            ProjectionExtension.add_to(item)
            proj_ext = ProjectionExtension.ext(item)
            proj_ext.epsg = 4326
        elif ext_name == "raster":
            RasterExtension.add_to(item)
        elif ext_name == "processing" and PROCESSING_EXTENSION_AVAILABLE:
            ProcessingExtension.add_to(item)

    href_resolver = HrefResolver(config, layout)
    analyzer_output = publish_item.analyzer_output

    primary_asset = analyzer_output.primary_cog_asset
    primary_href = href_resolver.resolve_cog_asset_href(
        publish_item.item_id, primary_asset.key
    )

    primary_roles = list(primary_asset.roles or [])
    if "data" not in primary_roles:
        primary_roles.append("data")
    if "primary" not in primary_roles:
        primary_roles.append("primary")

    pystac_asset = pystac.Asset(
        href=primary_href,
        title=primary_asset.title,
        description=primary_asset.description,
        media_type=primary_asset.media_type
        or "image/tiff; application=geotiff; profile=cloud-optimized",
        roles=primary_roles,
        extra_fields=primary_asset.extra_fields or {},
    )

    item.add_asset(primary_asset.key, pystac_asset)

    if analyzer_output.additional_assets:
        for asset_spec in analyzer_output.additional_assets:
            if "thumbnail" in (asset_spec.roles or []):
                asset_href = href_resolver.resolve_thumbnail_href(
                    publish_item.item_id, asset_spec.key
                )
            else:
                asset_href = href_resolver.resolve_thumbnail_href(
                    publish_item.item_id, asset_spec.key
                )

            additional_asset = pystac.Asset(
                href=asset_href,
                title=asset_spec.title,
                description=asset_spec.description,
                media_type=asset_spec.media_type,
                roles=asset_spec.roles,
                extra_fields=asset_spec.extra_fields or {},
            )

            item.add_asset(asset_spec.key, additional_asset)

    return item


def write_stac_catalog(
    plan: PublishPlan, config: GeoExhibitConfig, output_dir: Optional[Path] = None
) -> Dict[str, Any]:
    """Write complete STAC catalog for the publish plan."""
    layout = CanonicalLayout(plan.job_id)

    collection = create_stac_collection(plan, config, layout)
    
    # Add self link to collection to prevent null href issues
    collection_self_link = pystac.Link(
        rel="self",
        target="collection.json",
        media_type="application/json",
        title="This collection"
    )
    collection.add_link(collection_self_link)
    
    # Add root link to collection (pointing to itself for a standalone collection)
    collection_root_link = pystac.Link(
        rel="root",
        target="collection.json",
        media_type="application/json", 
        title="Root collection"
    )
    collection.add_link(collection_root_link)

    items = []
    for publish_item in plan.items:
        item = create_stac_item(publish_item, collection, config, layout)
        items.append(item)
    
    # Manually create item links in collection with proper relative hrefs
    # This prevents PySTAC from creating null hrefs in automatic links
    for item in items:
        item_link = pystac.Link(
            rel="item",
            target=f"items/{item.id}.json",
            media_type="application/json",
            title=f"Item {item.id}"
        )
        collection.add_link(item_link)
    
    # Manually create necessary links in items without null hrefs
    for item in items:
        # Remove any auto-generated links that might have null hrefs
        item.links = []
        
        # Add root link (pointing to collection) - set the target object directly to avoid resolution issues
        root_link = pystac.Link(
            rel="root",
            target="../collection.json",
            media_type="application/json",
            title="Root collection"
        )
        # Set the target object directly to avoid PySTAC trying to resolve the link during validation
        root_link._target_object = collection
        item.add_link(root_link)
        
        # Add parent/collection link - set the target object directly
        collection_link = pystac.Link(
            rel="collection",
            target="../collection.json",
            media_type="application/json",
            title="Parent collection"
        )
        # Set the target object directly to avoid PySTAC trying to resolve the link during validation
        collection_link._target_object = collection
        item.add_link(collection_link)
        
        # Add self link
        self_link = pystac.Link(
            rel="self",
            target=f"{item.id}.json",
            media_type="application/json",
            title=f"Item {item.id}"
        )
        item.add_link(self_link)

    if output_dir:
        job_dir = output_dir / f"jobs/{plan.job_id}"
        stac_dir = job_dir / "stac"
        items_dir = stac_dir / "items"

        stac_dir.mkdir(parents=True, exist_ok=True)
        items_dir.mkdir(parents=True, exist_ok=True)

        collection_path = stac_dir / "collection.json"
        item_paths = [items_dir / f"{item.id}.json" for item in items]
        
        # Actually write files to disk when output_dir is provided
        import json
        with open(collection_path, 'w', encoding='utf-8') as f:
            json.dump(collection.to_dict(), f, indent=2)
            
        for item, item_path in zip(items, item_paths):
            with open(item_path, 'w', encoding='utf-8') as f:
                # Fix item links to have proper relative hrefs in the JSON output
                item_dict = _fix_item_link_hrefs(item.to_dict())
                json.dump(item_dict, f, indent=2)
    else:
        collection_path = Path(layout.collection_path)
        item_paths = [Path(layout.item_path(item.id)) for item in items]

    _validate_stac_collection(collection)
    for item in items:
        _validate_stac_item(item, config)

    logger.info(f"Generated STAC catalog with {len(items)} items")

    return {
        "collection": {"path": str(collection_path), "object": collection},
        "items": [
            {"path": str(path), "object": item} for path, item in zip(item_paths, items)
        ],
        "job_id": plan.job_id,
        "collection_id": plan.collection_id,
        "layout": layout,
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

        primary_assets = [
            asset
            for asset in item.assets.values()
            if asset.roles and "primary" in asset.roles and "data" in asset.roles
        ]

        if not primary_assets:
            raise ValueError(
                f"STAC Item {item.id} missing primary COG asset with 'data' and 'primary' roles"
            )

        if len(primary_assets) > 1:
            logger.warning(f"STAC Item {item.id} has multiple primary assets")

        primary_asset = primary_assets[0]
        if not primary_asset.href.startswith("s3://"):
            raise ValueError(
                f"Primary COG asset HREF must be fully qualified S3 URL: {primary_asset.href}"
            )

        logger.debug(f"STAC Item {item.id} has valid primary COG asset")

    except Exception as e:
        raise ValueError(f"Invalid STAC Item {item.id}: {e}")
