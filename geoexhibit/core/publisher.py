"""Publishing functionality for uploading to S3 and local filesystems."""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
import pystac

from .interfaces import Publisher, PublishPlan, PublishItem, GeoExhibitConfig
from .stac_writer import write_stac_catalog, HrefResolver

logger = logging.getLogger(__name__)


class S3Publisher(Publisher):
    """Publisher that uploads assets and STAC metadata to S3."""
    
    def __init__(self, config: GeoExhibitConfig, dry_run: bool = False):
        """
        Initialize S3 publisher.
        
        Args:
            config: GeoExhibit configuration
            dry_run: If True, log operations without actually uploading
        """
        self.config = config
        self.dry_run = dry_run
        self.s3_bucket = config.s3_bucket
        
        try:
            # Use region from config if available
            if config.aws_region:
                self.s3_client = boto3.client('s3', region_name=config.aws_region)
            else:
                self.s3_client = boto3.client('s3')
            
            # Test connectivity
            if not dry_run:
                self.s3_client.head_bucket(Bucket=self.s3_bucket)
        except NoCredentialsError:
            raise ValueError("AWS credentials not found. Configure AWS credentials.")
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                raise ValueError(f"S3 bucket not found: {self.s3_bucket}")
            else:
                raise ValueError(f"Error accessing S3 bucket {self.s3_bucket}: {e}")
    
    def publish_plan(self, plan: PublishPlan) -> None:
        """
        Publish the complete plan to S3.
        
        Args:
            plan: PublishPlan with all items and metadata
        """
        logger.info(f"Publishing plan {plan.job_id} to S3 bucket: {self.s3_bucket}")
        
        # First, upload all assets
        self._upload_assets(plan)
        
        # Generate and upload STAC catalog
        stac_data = write_stac_catalog(plan, self.config)
        self._upload_stac_catalog(stac_data)
        
        # Upload PMTiles if present
        if plan.pmtiles_path:
            self._upload_pmtiles(plan)
        
        logger.info(f"Successfully published plan {plan.job_id}")
    
    def _upload_assets(self, plan: PublishPlan) -> None:
        """Upload all assets for all items in the plan."""
        href_resolver = HrefResolver(self.config, plan.job_id)
        
        for item in plan.items:
            logger.info(f"Uploading assets for item {item.item_id}")
            
            # Upload primary COG asset
            primary_asset = item.analyzer_output.primary_cog_asset
            s3_key = self._extract_s3_key_from_href(
                href_resolver.resolve_asset_href(primary_asset, is_cog=True)
            )
            self._upload_file(primary_asset.href, s3_key, primary_asset.media_type)
            
            # Upload additional assets
            if item.analyzer_output.additional_assets:
                for asset in item.analyzer_output.additional_assets:
                    s3_key = self._extract_s3_key_from_href(
                        href_resolver.resolve_asset_href(asset, is_cog=False)
                    )
                    self._upload_file(asset.href, s3_key, asset.media_type)
    
    def _upload_stac_catalog(self, stac_data: Dict[str, Any]) -> None:
        """Upload STAC collection and items to S3."""
        # Upload collection
        collection_path = stac_data["collection"]["path"]
        collection_obj = stac_data["collection"]["object"]
        
        collection_json = json.dumps(collection_obj.to_dict(), indent=2)
        self._upload_content(collection_json, collection_path, "application/json")
        
        # Upload items
        for item_data in stac_data["items"]:
            item_path = item_data["path"]
            item_obj = item_data["object"]
            
            item_json = json.dumps(item_obj.to_dict(), indent=2)
            self._upload_content(item_json, item_path, "application/json")
        
        logger.info(f"Uploaded STAC catalog: 1 collection, {len(stac_data['items'])} items")
    
    def _upload_pmtiles(self, plan: PublishPlan) -> None:
        """Upload PMTiles file to S3."""
        href_resolver = HrefResolver(self.config, plan.job_id)
        pmtiles_s3_path = href_resolver.resolve_pmtiles_href(plan.pmtiles_path)
        
        # Assume PMTiles file exists locally and needs to be uploaded
        local_pmtiles_path = Path(plan.pmtiles_path)
        if local_pmtiles_path.exists():
            self._upload_file(str(local_pmtiles_path), pmtiles_s3_path, "application/x-pmtiles")
        else:
            logger.warning(f"PMTiles file not found: {local_pmtiles_path}")
    
    def _upload_file(self, local_path: str, s3_key: str, content_type: Optional[str] = None) -> None:
        """Upload a local file to S3."""
        local_file_path = Path(local_path)
        
        if not local_file_path.exists():
            raise FileNotFoundError(f"Local file not found: {local_path}")
        
        extra_args = {}
        if content_type:
            extra_args['ContentType'] = content_type
        
        if self.dry_run:
            logger.info(f"DRY RUN: Would upload {local_path} to s3://{self.s3_bucket}/{s3_key}")
            return
        
        try:
            self.s3_client.upload_file(str(local_file_path), self.s3_bucket, s3_key, ExtraArgs=extra_args)
            logger.debug(f"Uploaded {local_path} to s3://{self.s3_bucket}/{s3_key}")
        except ClientError as e:
            raise RuntimeError(f"Failed to upload {local_path} to S3: {e}")
    
    def _upload_content(self, content: str, s3_key: str, content_type: str) -> None:
        """Upload string content directly to S3."""
        if self.dry_run:
            logger.info(f"DRY RUN: Would upload content to s3://{self.s3_bucket}/{s3_key}")
            return
        
        try:
            self.s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=s3_key,
                Body=content,
                ContentType=content_type
            )
            logger.debug(f"Uploaded content to s3://{self.s3_bucket}/{s3_key}")
        except ClientError as e:
            raise RuntimeError(f"Failed to upload content to S3: {e}")
    
    def _extract_s3_key_from_href(self, href: str) -> str:
        """Extract S3 key from a full S3 HREF."""
        if not href.startswith('s3://'):
            # Relative path, treat as key directly
            return href
        
        # Remove s3://bucket/ prefix
        bucket_prefix = f"s3://{self.s3_bucket}/"
        if href.startswith(bucket_prefix):
            return href[len(bucket_prefix):]
        else:
            # Different bucket in HREF
            parts = href[5:].split('/', 1)  # Remove s3:// and split
            if len(parts) == 2:
                return parts[1]  # Return key part
            else:
                raise ValueError(f"Invalid S3 HREF format: {href}")
    
    def verify_publication(self, plan: PublishPlan) -> bool:
        """
        Verify that the plan was published correctly using AWS APIs.
        
        Args:
            plan: PublishPlan that was published
            
        Returns:
            True if verification passes, False otherwise
        """
        logger.info(f"Verifying publication of plan {plan.job_id}")
        
        if self.dry_run:
            logger.info("DRY RUN: Skipping publication verification")
            return True
        
        try:
            # Verify collection JSON
            collection_verified = self._verify_collection(plan)
            
            # Verify all items
            items_verified = self._verify_items(plan)
            
            # Verify primary COGs
            cogs_verified = self._verify_primary_cogs(plan)
            
            # Verify PMTiles if present
            pmtiles_verified = True
            if plan.pmtiles_path:
                pmtiles_verified = self._verify_pmtiles(plan)
            
            verification_passed = collection_verified and items_verified and cogs_verified and pmtiles_verified
            
            if verification_passed:
                logger.info(f"Publication verification passed for plan {plan.job_id}")
            else:
                logger.error(f"Publication verification failed for plan {plan.job_id}")
            
            return verification_passed
            
        except Exception as e:
            logger.error(f"Publication verification error: {e}")
            return False
    
    def _verify_collection(self, plan: PublishPlan) -> bool:
        """Verify collection JSON exists and is valid."""
        href_resolver = HrefResolver(self.config, plan.job_id)
        collection_key = href_resolver.resolve_stac_href(f"{plan.collection_id}.json", "collection")
        
        try:
            response = self.s3_client.get_object(Bucket=self.s3_bucket, Key=collection_key)
            collection_data = json.loads(response['Body'].read().decode('utf-8'))
            
            # Validate it's a proper STAC collection
            if collection_data.get('type') != 'Collection':
                logger.error("Collection JSON missing type=Collection")
                return False
            
            if collection_data.get('id') != plan.collection_id:
                logger.error(f"Collection ID mismatch: expected {plan.collection_id}, got {collection_data.get('id')}")
                return False
            
            logger.debug(f"Collection verification passed: {collection_key}")
            return True
            
        except ClientError as e:
            logger.error(f"Collection verification failed: {e}")
            return False
    
    def _verify_items(self, plan: PublishPlan) -> bool:
        """Verify all item JSONs exist and are valid."""
        href_resolver = HrefResolver(self.config, plan.job_id)
        
        for item in plan.items:
            item_key = href_resolver.resolve_stac_href(f"{item.item_id}.json", "item")
            
            try:
                response = self.s3_client.get_object(Bucket=self.s3_bucket, Key=item_key)
                item_data = json.loads(response['Body'].read().decode('utf-8'))
                
                # Validate it's a proper STAC item
                if item_data.get('type') != 'Feature':
                    logger.error(f"Item {item.item_id} JSON missing type=Feature")
                    return False
                
                if item_data.get('id') != item.item_id:
                    logger.error(f"Item ID mismatch: expected {item.item_id}, got {item_data.get('id')}")
                    return False
                
                # Verify primary asset exists
                assets = item_data.get('assets', {})
                primary_assets = [
                    asset for asset in assets.values()
                    if isinstance(asset.get('roles'), list) and 'primary' in asset['roles'] and 'data' in asset['roles']
                ]
                
                if not primary_assets:
                    logger.error(f"Item {item.item_id} missing primary asset")
                    return False
                
                logger.debug(f"Item verification passed: {item_key}")
                
            except ClientError as e:
                logger.error(f"Item {item.item_id} verification failed: {e}")
                return False
        
        return True
    
    def _verify_primary_cogs(self, plan: PublishPlan) -> bool:
        """Verify all primary COG files exist in S3."""
        href_resolver = HrefResolver(self.config, plan.job_id)
        
        for item in plan.items:
            primary_asset = item.analyzer_output.primary_cog_asset
            cog_s3_key = self._extract_s3_key_from_href(
                href_resolver.resolve_asset_href(primary_asset, is_cog=True)
            )
            
            try:
                # Just check if object exists
                self.s3_client.head_object(Bucket=self.s3_bucket, Key=cog_s3_key)
                logger.debug(f"Primary COG verification passed: {cog_s3_key}")
                
            except ClientError as e:
                logger.error(f"Primary COG {cog_s3_key} verification failed: {e}")
                return False
        
        return True
    
    def _verify_pmtiles(self, plan: PublishPlan) -> bool:
        """Verify PMTiles file exists in S3."""
        href_resolver = HrefResolver(self.config, plan.job_id)
        pmtiles_key = href_resolver.resolve_pmtiles_href(plan.pmtiles_path)
        
        try:
            self.s3_client.head_object(Bucket=self.s3_bucket, Key=pmtiles_key)
            logger.debug(f"PMTiles verification passed: {pmtiles_key}")
            return True
            
        except ClientError as e:
            logger.error(f"PMTiles {pmtiles_key} verification failed: {e}")
            return False


class LocalPublisher(Publisher):
    """Publisher that writes assets and STAC metadata to local filesystem."""
    
    def __init__(self, output_dir: Path):
        """
        Initialize local publisher.
        
        Args:
            output_dir: Directory to write all outputs
        """
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def publish_plan(self, plan: PublishPlan) -> None:
        """
        Publish the complete plan to local filesystem.
        
        Args:
            plan: PublishPlan with all items and metadata
        """
        logger.info(f"Publishing plan {plan.job_id} to local directory: {self.output_dir}")
        
        # Create directory structure
        assets_dir = self.output_dir / "assets"
        assets_dir.mkdir(exist_ok=True)
        
        # Copy assets to local directory
        self._copy_assets(plan, assets_dir)
        
        # Generate and write STAC catalog
        stac_data = write_stac_catalog(plan, self.config, self.output_dir)
        self._write_stac_files(stac_data)
        
        # Copy PMTiles if present
        if plan.pmtiles_path:
            self._copy_pmtiles(plan)
        
        logger.info(f"Successfully published plan {plan.job_id} locally")
    
    def _copy_assets(self, plan: PublishPlan, assets_dir: Path) -> None:
        """Copy all assets to local directory."""
        import shutil
        
        for item in plan.items:
            # Copy primary COG
            primary_asset = item.analyzer_output.primary_cog_asset
            if Path(primary_asset.href).exists():
                dest = assets_dir / Path(primary_asset.href).name
                shutil.copy2(primary_asset.href, dest)
                logger.debug(f"Copied {primary_asset.href} to {dest}")
            
            # Copy additional assets
            if item.analyzer_output.additional_assets:
                for asset in item.analyzer_output.additional_assets:
                    if Path(asset.href).exists():
                        dest = assets_dir / Path(asset.href).name
                        shutil.copy2(asset.href, dest)
                        logger.debug(f"Copied {asset.href} to {dest}")
    
    def _write_stac_files(self, stac_data: Dict[str, Any]) -> None:
        """Write STAC files to local filesystem."""
        # Collection already has the correct path from write_stac_catalog
        collection_path = Path(stac_data["collection"]["path"])
        collection_obj = stac_data["collection"]["object"]
        
        collection_path.parent.mkdir(parents=True, exist_ok=True)
        with open(collection_path, 'w') as f:
            json.dump(collection_obj.to_dict(), f, indent=2)
        
        # Items
        for item_data in stac_data["items"]:
            item_path = Path(item_data["path"])
            item_obj = item_data["object"]
            
            item_path.parent.mkdir(parents=True, exist_ok=True)
            with open(item_path, 'w') as f:
                json.dump(item_obj.to_dict(), f, indent=2)
    
    def _copy_pmtiles(self, plan: PublishPlan) -> None:
        """Copy PMTiles to local directory."""
        import shutil
        
        pmtiles_dir = self.output_dir / "pmtiles"
        pmtiles_dir.mkdir(exist_ok=True)
        
        source_path = Path(plan.pmtiles_path)
        if source_path.exists():
            dest_path = pmtiles_dir / source_path.name
            shutil.copy2(source_path, dest_path)
            logger.debug(f"Copied PMTiles {source_path} to {dest_path}")
    
    def verify_publication(self, plan: PublishPlan) -> bool:
        """Verify that files were written correctly to local filesystem."""
        logger.info(f"Verifying local publication of plan {plan.job_id}")
        
        # Check STAC files exist
        stac_dir = self.output_dir / "stac"
        collection_file = stac_dir / "collections" / f"{plan.collection_id}.json"
        
        if not collection_file.exists():
            logger.error(f"Collection file not found: {collection_file}")
            return False
        
        # Check item files
        items_dir = stac_dir / "items"
        for item in plan.items:
            item_file = items_dir / f"{item.item_id}.json"
            if not item_file.exists():
                logger.error(f"Item file not found: {item_file}")
                return False
        
        logger.info(f"Local publication verification passed for plan {plan.job_id}")
        return True


def create_publisher(config: GeoExhibitConfig, local_out_dir: Optional[Path] = None, 
                   dry_run: bool = False) -> Publisher:
    """
    Create appropriate publisher based on configuration.
    
    Args:
        config: GeoExhibit configuration
        local_out_dir: If provided, use LocalPublisher instead of S3Publisher
        dry_run: If True, create S3Publisher in dry-run mode
        
    Returns:
        Configured Publisher instance
    """
    if local_out_dir:
        return LocalPublisher(local_out_dir)
    else:
        return S3Publisher(config, dry_run=dry_run)