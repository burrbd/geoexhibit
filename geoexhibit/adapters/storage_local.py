"""Local filesystem storage adapter for GeoExhibit."""

import json
import shutil
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class LocalStorageAdapter:
    """Adapter for local filesystem operations."""
    
    def __init__(self, base_dir: Path):
        """
        Initialize local storage adapter.
        
        Args:
            base_dir: Base directory for all storage operations
        """
        self.base_dir = Path(base_dir).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)
    
    def write_file(self, content: str, relative_path: str, create_dirs: bool = True) -> Path:
        """
        Write string content to a file.
        
        Args:
            content: Content to write
            relative_path: Path relative to base_dir
            create_dirs: Whether to create parent directories
            
        Returns:
            Absolute path to the written file
        """
        file_path = self.base_dir / relative_path
        
        if create_dirs:
            file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.debug(f"Wrote file: {file_path}")
        return file_path
    
    def write_json(self, data: Dict[str, Any], relative_path: str, create_dirs: bool = True) -> Path:
        """
        Write JSON data to a file.
        
        Args:
            data: Data to write as JSON
            relative_path: Path relative to base_dir
            create_dirs: Whether to create parent directories
            
        Returns:
            Absolute path to the written file
        """
        json_content = json.dumps(data, indent=2, ensure_ascii=False)
        return self.write_file(json_content, relative_path, create_dirs)
    
    def copy_file(self, source_path: Path, relative_dest: str, create_dirs: bool = True) -> Path:
        """
        Copy a file to the storage directory.
        
        Args:
            source_path: Path to source file
            relative_dest: Destination path relative to base_dir
            create_dirs: Whether to create parent directories
            
        Returns:
            Absolute path to the copied file
            
        Raises:
            FileNotFoundError: If source file doesn't exist
        """
        if not source_path.exists():
            raise FileNotFoundError(f"Source file not found: {source_path}")
        
        dest_path = self.base_dir / relative_dest
        
        if create_dirs:
            dest_path.parent.mkdir(parents=True, exist_ok=True)
        
        shutil.copy2(source_path, dest_path)
        logger.debug(f"Copied {source_path} to {dest_path}")
        return dest_path
    
    def read_file(self, relative_path: str) -> str:
        """
        Read string content from a file.
        
        Args:
            relative_path: Path relative to base_dir
            
        Returns:
            File content as string
            
        Raises:
            FileNotFoundError: If file doesn't exist
        """
        file_path = self.base_dir / relative_path
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def read_json(self, relative_path: str) -> Dict[str, Any]:
        """
        Read JSON data from a file.
        
        Args:
            relative_path: Path relative to base_dir
            
        Returns:
            Parsed JSON data
            
        Raises:
            FileNotFoundError: If file doesn't exist
            json.JSONDecodeError: If file contains invalid JSON
        """
        content = self.read_file(relative_path)
        return json.loads(content)
    
    def exists(self, relative_path: str) -> bool:
        """
        Check if a file or directory exists.
        
        Args:
            relative_path: Path relative to base_dir
            
        Returns:
            True if exists, False otherwise
        """
        return (self.base_dir / relative_path).exists()
    
    def list_files(self, relative_dir: str = "", pattern: str = "*", recursive: bool = False) -> List[Path]:
        """
        List files in a directory.
        
        Args:
            relative_dir: Directory relative to base_dir
            pattern: Glob pattern for matching files
            recursive: Whether to search recursively
            
        Returns:
            List of absolute paths to matching files
        """
        search_dir = self.base_dir / relative_dir
        
        if not search_dir.exists():
            return []
        
        if recursive:
            return list(search_dir.rglob(pattern))
        else:
            return list(search_dir.glob(pattern))
    
    def delete_file(self, relative_path: str) -> None:
        """
        Delete a file.
        
        Args:
            relative_path: Path relative to base_dir
            
        Raises:
            FileNotFoundError: If file doesn't exist
        """
        file_path = self.base_dir / relative_path
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if file_path.is_dir():
            shutil.rmtree(file_path)
        else:
            file_path.unlink()
        
        logger.debug(f"Deleted: {file_path}")
    
    def get_file_info(self, relative_path: str) -> Dict[str, Any]:
        """
        Get information about a file.
        
        Args:
            relative_path: Path relative to base_dir
            
        Returns:
            Dictionary with file information
            
        Raises:
            FileNotFoundError: If file doesn't exist
        """
        file_path = self.base_dir / relative_path
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        stat = file_path.stat()
        return {
            'size': stat.st_size,
            'modified': stat.st_mtime,
            'is_dir': file_path.is_dir(),
            'is_file': file_path.is_file(),
            'absolute_path': str(file_path)
        }
    
    def create_directory(self, relative_path: str, exist_ok: bool = True) -> Path:
        """
        Create a directory.
        
        Args:
            relative_path: Directory path relative to base_dir
            exist_ok: Don't raise error if directory already exists
            
        Returns:
            Absolute path to the created directory
        """
        dir_path = self.base_dir / relative_path
        dir_path.mkdir(parents=True, exist_ok=exist_ok)
        logger.debug(f"Created directory: {dir_path}")
        return dir_path
    
    def get_absolute_path(self, relative_path: str) -> Path:
        """
        Get absolute path for a relative path.
        
        Args:
            relative_path: Path relative to base_dir
            
        Returns:
            Absolute path
        """
        return self.base_dir / relative_path
    
    def get_relative_path(self, absolute_path: Path) -> str:
        """
        Get relative path from an absolute path.
        
        Args:
            absolute_path: Absolute path
            
        Returns:
            Path relative to base_dir
            
        Raises:
            ValueError: If absolute_path is not under base_dir
        """
        try:
            return str(absolute_path.relative_to(self.base_dir))
        except ValueError:
            raise ValueError(f"Path {absolute_path} is not under base directory {self.base_dir}")


def create_local_adapter(base_dir: Path) -> LocalStorageAdapter:
    """
    Create and initialize local storage adapter.
    
    Args:
        base_dir: Base directory for storage
        
    Returns:
        Configured LocalStorageAdapter
    """
    return LocalStorageAdapter(base_dir)