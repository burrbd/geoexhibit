"""Analyzer interface for GeoExhibit."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, List, Optional

from .timespan import TimeSpan


@dataclass
class AssetSpec:
    """Specification for a STAC asset."""

    key: str
    href: str
    title: Optional[str] = None
    description: Optional[str] = None
    media_type: Optional[str] = None
    roles: Optional[List[str]] = None


@dataclass
class AnalyzerOutput:
    """Output from an analyzer for a single feature/time combination."""

    primary_cog_asset: AssetSpec
    additional_assets: Optional[List[AssetSpec]] = None
    extra_properties: Optional[Dict[str, Any]] = None

    @property
    def all_assets(self) -> List[AssetSpec]:
        """Get all assets including primary and additional."""
        assets = [self.primary_cog_asset]
        if self.additional_assets:
            assets.extend(self.additional_assets)
        return assets


class Analyzer(ABC):
    """Analyzer for generating raster outputs from feature/time combinations."""

    @abstractmethod
    def analyze(
        self,
        feature: Dict[str, Any],
        timespan: TimeSpan,
    ) -> AnalyzerOutput:
        """Analyze a feature at a specific time and return outputs."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of this analyzer."""
        pass
