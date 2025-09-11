"""S3 storage adapter for GeoExhibit."""

import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

logger = logging.getLogger(__name__)


class S3StorageAdapter:
    """Adapter for S3 operations."""
    
    def __init__(self, bucket: str, region: Optional[str] = None):
        """
        Initialize S3 adapter.
        
        Args:
            bucket: S3 bucket name
            region: AWS region (optional, uses default if not specified)
        """
        self.bucket = bucket
        self.region = region
        
        try:
            if region:
                self.s3_client = boto3.client('s3', region_name=region)
            else:
                self.s3_client = boto3.client('s3')
            
            # Test connectivity
            self.s3_client.head_bucket(Bucket=bucket)
            
        except NoCredentialsError:
            raise ValueError("AWS credentials not found. Configure AWS credentials.")
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                raise ValueError(f"S3 bucket not found: {bucket}")
            else:
                raise ValueError(f"Error accessing S3 bucket {bucket}: {e}")
    
    def upload_file(self, local_path: Path, s3_key: str, content_type: Optional[str] = None) -> None:
        """
        Upload a file to S3.
        
        Args:
            local_path: Path to local file
            s3_key: S3 key for the uploaded file
            content_type: Content type for the file
            
        Raises:
            FileNotFoundError: If local file doesn't exist
            RuntimeError: If upload fails
        """
        if not local_path.exists():
            raise FileNotFoundError(f"Local file not found: {local_path}")
        
        extra_args = {}
        if content_type:
            extra_args['ContentType'] = content_type
        
        try:
            self.s3_client.upload_file(str(local_path), self.bucket, s3_key, ExtraArgs=extra_args)
            logger.debug(f"Uploaded {local_path} to s3://{self.bucket}/{s3_key}")
        except ClientError as e:
            raise RuntimeError(f"Failed to upload {local_path} to S3: {e}")
    
    def upload_content(self, content: str, s3_key: str, content_type: str = 'text/plain') -> None:
        """
        Upload string content directly to S3.
        
        Args:
            content: String content to upload
            s3_key: S3 key for the content
            content_type: Content type
            
        Raises:
            RuntimeError: If upload fails
        """
        try:
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=s3_key,
                Body=content,
                ContentType=content_type
            )
            logger.debug(f"Uploaded content to s3://{self.bucket}/{s3_key}")
        except ClientError as e:
            raise RuntimeError(f"Failed to upload content to S3: {e}")
    
    def download_file(self, s3_key: str, local_path: Path) -> None:
        """
        Download a file from S3.
        
        Args:
            s3_key: S3 key of the file to download
            local_path: Local path to save the file
            
        Raises:
            RuntimeError: If download fails
        """
        try:
            local_path.parent.mkdir(parents=True, exist_ok=True)
            self.s3_client.download_file(self.bucket, s3_key, str(local_path))
            logger.debug(f"Downloaded s3://{self.bucket}/{s3_key} to {local_path}")
        except ClientError as e:
            raise RuntimeError(f"Failed to download s3://{self.bucket}/{s3_key}: {e}")
    
    def get_content(self, s3_key: str) -> str:
        """
        Get string content from S3.
        
        Args:
            s3_key: S3 key of the object
            
        Returns:
            String content of the object
            
        Raises:
            RuntimeError: If download fails
        """
        try:
            response = self.s3_client.get_object(Bucket=self.bucket, Key=s3_key)
            return response['Body'].read().decode('utf-8')
        except ClientError as e:
            raise RuntimeError(f"Failed to get content from s3://{self.bucket}/{s3_key}: {e}")
    
    def exists(self, s3_key: str) -> bool:
        """
        Check if an object exists in S3.
        
        Args:
            s3_key: S3 key to check
            
        Returns:
            True if object exists, False otherwise
        """
        try:
            self.s3_client.head_object(Bucket=self.bucket, Key=s3_key)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            else:
                raise RuntimeError(f"Error checking s3://{self.bucket}/{s3_key}: {e}")
    
    def list_objects(self, prefix: str = '', max_keys: int = 1000) -> List[Dict[str, Any]]:
        """
        List objects in S3 with given prefix.
        
        Args:
            prefix: Key prefix to filter objects
            max_keys: Maximum number of objects to return
            
        Returns:
            List of object metadata dictionaries
        """
        try:
            paginator = self.s3_client.get_paginator('list_objects_v2')
            page_iterator = paginator.paginate(
                Bucket=self.bucket,
                Prefix=prefix,
                PaginationConfig={'MaxItems': max_keys}
            )
            
            objects = []
            for page in page_iterator:
                if 'Contents' in page:
                    objects.extend(page['Contents'])
            
            return objects
            
        except ClientError as e:
            raise RuntimeError(f"Failed to list objects with prefix {prefix}: {e}")
    
    def delete_object(self, s3_key: str) -> None:
        """
        Delete an object from S3.
        
        Args:
            s3_key: S3 key of the object to delete
            
        Raises:
            RuntimeError: If deletion fails
        """
        try:
            self.s3_client.delete_object(Bucket=self.bucket, Key=s3_key)
            logger.debug(f"Deleted s3://{self.bucket}/{s3_key}")
        except ClientError as e:
            raise RuntimeError(f"Failed to delete s3://{self.bucket}/{s3_key}: {e}")
    
    def get_object_info(self, s3_key: str) -> Dict[str, Any]:
        """
        Get metadata about an S3 object.
        
        Args:
            s3_key: S3 key of the object
            
        Returns:
            Dictionary with object metadata
            
        Raises:
            RuntimeError: If operation fails
        """
        try:
            response = self.s3_client.head_object(Bucket=self.bucket, Key=s3_key)
            return {
                'size': response.get('ContentLength'),
                'last_modified': response.get('LastModified'),
                'content_type': response.get('ContentType'),
                'etag': response.get('ETag'),
                'metadata': response.get('Metadata', {})
            }
        except ClientError as e:
            raise RuntimeError(f"Failed to get info for s3://{self.bucket}/{s3_key}: {e}")
    
    def copy_object(self, source_key: str, dest_key: str, source_bucket: Optional[str] = None) -> None:
        """
        Copy an object within S3.
        
        Args:
            source_key: Source S3 key
            dest_key: Destination S3 key
            source_bucket: Source bucket (defaults to same bucket)
            
        Raises:
            RuntimeError: If copy fails
        """
        source_bucket = source_bucket or self.bucket
        copy_source = {'Bucket': source_bucket, 'Key': source_key}
        
        try:
            self.s3_client.copy_object(
                CopySource=copy_source,
                Bucket=self.bucket,
                Key=dest_key
            )
            logger.debug(f"Copied s3://{source_bucket}/{source_key} to s3://{self.bucket}/{dest_key}")
        except ClientError as e:
            raise RuntimeError(f"Failed to copy object: {e}")


def create_s3_adapter(bucket: str, region: Optional[str] = None) -> S3StorageAdapter:
    """
    Create and validate S3 storage adapter.
    
    Args:
        bucket: S3 bucket name
        region: AWS region
        
    Returns:
        Configured S3StorageAdapter
    """
    return S3StorageAdapter(bucket, region)