"""Canonical S3/STAC layout paths for GeoExhibit."""

from dataclasses import dataclass


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
