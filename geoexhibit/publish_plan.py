"""Publishing plan data structures for GeoExhibit."""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

from .analyzer import AnalyzerOutput
from .timespan import TimeSpan


@dataclass
class PublishItem:
    """A STAC Item to be published with all its assets."""

    item_id: str
    feature: Dict[str, Any]
    timespan: TimeSpan
    analyzer_output: AnalyzerOutput

    @property
    def geometry(self) -> Dict[str, Any]:
        """Get the geometry from the feature."""
        geometry = self.feature["geometry"]
        assert isinstance(geometry, dict)
        return geometry

    @property
    def properties(self) -> Dict[str, Any]:
        """Get combined properties from feature and analyzer output."""
        feature_props = self.feature.get("properties", {})
        assert isinstance(feature_props, dict)
        props = feature_props.copy()

        if self.analyzer_output.extra_properties:
            props.update(self.analyzer_output.extra_properties)
        return props

    @property
    def feature_id(self) -> str:
        """Get the feature_id from properties."""
        feature_id = self.properties.get("feature_id", self.item_id)
        assert isinstance(feature_id, str)
        return feature_id


@dataclass
class PublishPlan:
    """Complete plan for publishing a collection and its items."""

    collection_id: str
    job_id: str
    items: List[PublishItem]
    collection_metadata: Dict[str, Any]
    pmtiles_path: Optional[str] = None

    @property
    def item_count(self) -> int:
        """Get number of items in this plan."""
        return len(self.items)

    @property
    def feature_count(self) -> int:
        """Get number of unique features in this plan."""
        feature_ids = {item.feature_id for item in self.items}
        return len(feature_ids)

    @property
    def time_range(self) -> Tuple[datetime, datetime]:
        """Get the overall time range covered by this plan."""
        if not self.items:
            raise ValueError("Cannot get time range from empty publish plan")

        start_times = [item.timespan.start for item in self.items]
        end_times = [
            item.timespan.end if item.timespan.end else item.timespan.start
            for item in self.items
        ]

        return min(start_times), max(end_times)

    def get_items_for_feature(self, feature_id: str) -> List[PublishItem]:
        """Get all items for a specific feature."""
        return [item for item in self.items if item.feature_id == feature_id]

    def validate(self) -> None:
        """Validate the publish plan for consistency and completeness."""
        if not self.items:
            raise ValueError("Publish plan must contain at least one item")

        if not self.collection_id:
            raise ValueError("Publish plan must have a collection_id")

        if not self.job_id:
            raise ValueError("Publish plan must have a job_id")

        for i, item in enumerate(self.items):
            if not item.item_id:
                raise ValueError(f"Item {i} missing item_id")

            if not item.feature.get("geometry"):
                raise ValueError(f"Item {i} missing geometry")

            if not item.analyzer_output.primary_cog_asset:
                raise ValueError(f"Item {i} missing primary COG asset")

        duplicates = {}
        for item in self.items:
            if item.item_id in duplicates:
                raise ValueError(f"Duplicate item_id: {item.item_id}")
            duplicates[item.item_id] = True
