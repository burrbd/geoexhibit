"""Core interfaces and data models for GeoExhibit."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Iterable, Union
import pystac


@dataclass
class TimeSpan:
    """Represents a time span for analysis."""
    start: datetime
    end: Optional[datetime] = None
    
    @property
    def is_instant(self) -> bool:
        """True if this represents an instant in time."""
        return self.end is None
    
    def to_stac_datetime(self) -> Union[datetime, str]:
        """Convert to STAC-compatible datetime format."""
        if self.is_instant:
            return self.start
        return f"{self.start.isoformat()}Z/{self.end.isoformat()}Z"


@dataclass
class AssetSpec:
    """Specification for a STAC asset."""
    key: str
    href: str  # Will be resolved according to HREF rules
    title: Optional[str] = None
    description: Optional[str] = None
    media_type: Optional[str] = None
    roles: Optional[List[str]] = None
    extra_fields: Optional[Dict[str, Any]] = None


@dataclass
class AnalyzerOutput:
    """Output from an analyzer for a single feature/time combination."""
    primary_cog_asset: AssetSpec  # The primary COG asset that TiTiler can use
    additional_assets: Optional[List[AssetSpec]] = None  # Thumbnails, metadata, etc.
    extra_properties: Optional[Dict[str, Any]] = None  # Additional STAC Item properties
    
    @property
    def all_assets(self) -> List[AssetSpec]:
        """Get all assets including primary and additional."""
        assets = [self.primary_cog_asset]
        if self.additional_assets:
            assets.extend(self.additional_assets)
        return assets


@dataclass
class PublishItem:
    """A STAC Item to be published with all its assets."""
    item_id: str  # ULID
    feature: Dict[str, Any]  # GeoJSON feature
    timespan: TimeSpan
    analyzer_output: AnalyzerOutput
    
    @property
    def geometry(self) -> Dict[str, Any]:
        """Get the geometry from the feature."""
        return self.feature["geometry"]
    
    @property
    def properties(self) -> Dict[str, Any]:
        """Get combined properties."""
        props = self.feature.get("properties", {}).copy()
        if self.analyzer_output.extra_properties:
            props.update(self.analyzer_output.extra_properties)
        return props


@dataclass
class PublishPlan:
    """Complete plan for publishing a collection and its items."""
    collection_id: str
    job_id: str  # ULID for this publishing run
    items: List[PublishItem]
    collection_metadata: Dict[str, Any]
    pmtiles_path: Optional[str] = None  # Relative path to PMTiles file


class TimeProvider(ABC):
    """Provider for extracting time information from features."""
    
    @abstractmethod
    def for_feature(self, feature: Dict[str, Any]) -> Iterable[TimeSpan]:
        """Extract time spans for the given feature."""
        pass


class Analyzer(ABC):
    """Analyzer for generating raster outputs from feature/time combinations."""
    
    @abstractmethod
    def analyze(self, feature: Dict[str, Any], timespan: TimeSpan) -> AnalyzerOutput:
        """Analyze a feature at a specific time and return outputs."""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Name of this analyzer."""
        pass


class Publisher(ABC):
    """Publisher for uploading assets and STAC metadata."""
    
    @abstractmethod
    def publish_plan(self, plan: PublishPlan) -> None:
        """Publish the complete plan to the target destination."""
        pass
    
    @abstractmethod
    def verify_publication(self, plan: PublishPlan) -> bool:
        """Verify that the plan was published correctly."""
        pass


@dataclass
class GeoExhibitConfig:
    """Main configuration for GeoExhibit."""
    project: Dict[str, Any]
    aws: Dict[str, Any]
    map: Dict[str, Any]
    stac: Dict[str, Any]
    ids: Dict[str, Any]
    time: Dict[str, Any]
    
    @property
    def s3_bucket(self) -> str:
        """Get S3 bucket name."""
        return self.aws["s3_bucket"]
    
    @property
    def aws_region(self) -> Optional[str]:
        """Get AWS region (optional)."""
        return self.aws.get("region")
    
    @property
    def collection_id(self) -> str:
        """Get collection ID."""
        return self.project["collection_id"]
    
    @property
    def use_extensions(self) -> List[str]:
        """Get STAC extensions to use."""
        return self.stac.get("use_extensions", [])
    
    @property
    def project_name(self) -> str:
        """Get project name."""
        return self.project["name"]
    
    @property
    def time_config(self) -> Dict[str, Any]:
        """Get time provider configuration."""
        return self.time


@dataclass
class CanonicalLayout:
    """
    Canonical S3/STAC layout paths for GeoExhibit.
    This layout is hard-coded and not configurable by users.
    """
    job_id: str
    
    @property
    def job_root(self) -> str:
        """Root path for this job: jobs/<job_id>/"""
        return f"jobs/{self.job_id}/"
    
    @property
    def stac_root(self) -> str:
        """STAC root path: jobs/<job_id>/stac/"""
        return f"{self.job_root}stac/"
    
    @property
    def collection_path(self) -> str:
        """Collection JSON path: jobs/<job_id>/stac/collection.json"""
        return f"{self.stac_root}collection.json"
    
    @property
    def items_root(self) -> str:
        """Items directory: jobs/<job_id>/stac/items/"""
        return f"{self.stac_root}items/"
    
    def item_path(self, item_id: str) -> str:
        """Item JSON path: jobs/<job_id>/stac/items/<item_id>.json"""
        return f"{self.items_root}{item_id}.json"
    
    @property
    def pmtiles_root(self) -> str:
        """PMTiles directory: jobs/<job_id>/pmtiles/"""
        return f"{self.job_root}pmtiles/"
    
    @property
    def pmtiles_path(self) -> str:
        """Standard PMTiles file path: jobs/<job_id>/pmtiles/features.pmtiles"""
        return f"{self.pmtiles_root}features.pmtiles"
    
    @property
    def assets_root(self) -> str:
        """Assets directory: jobs/<job_id>/assets/"""
        return f"{self.job_root}assets/"
    
    def asset_path(self, item_id: str, asset_name: str) -> str:
        """Asset path: jobs/<job_id>/assets/<item_id>/<asset_name>"""
        return f"{self.assets_root}{item_id}/{asset_name}"
    
    @property
    def thumbs_root(self) -> str:
        """Thumbnails directory: jobs/<job_id>/thumbs/"""
        return f"{self.job_root}thumbs/"
    
    def thumb_path(self, item_id: str, thumb_name: str) -> str:
        """Thumbnail path: jobs/<job_id>/thumbs/<item_id>/<thumb_name>"""
        return f"{self.thumbs_root}{item_id}/{thumb_name}"