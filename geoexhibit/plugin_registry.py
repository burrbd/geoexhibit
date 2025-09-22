"""Plugin registry system for analyzers in GeoExhibit."""

import importlib
import importlib.util
import inspect
import logging
from pathlib import Path
from typing import Dict, Type, Optional, Any, List
import sys

from .analyzer import Analyzer

logger = logging.getLogger(__name__)


class AnalyzerRegistry:
    """Registry for analyzer plugins with decorator-based registration."""
    
    def __init__(self) -> None:
        self._analyzers: Dict[str, Type[Analyzer]] = {}
        self._auto_discovered: bool = False
    
    def register(self, name: str) -> callable:
        """
        Decorator to register an analyzer plugin.
        
        Usage:
            @analyzer.register("my_analyzer")
            class MyAnalyzer(Analyzer):
                # implementation
        """
        def decorator(cls: Type[Analyzer]) -> Type[Analyzer]:
            self._validate_analyzer_class(cls, name)
            self._analyzers[name] = cls
            logger.debug(f"Registered analyzer: {name} -> {cls.__name__}")
            return cls
        return decorator
    
    def get_analyzer(self, name: str, **kwargs: Any) -> Analyzer:
        """
        Get analyzer instance by name.
        
        Args:
            name: Analyzer name from config
            **kwargs: Arguments to pass to analyzer constructor
            
        Returns:
            Analyzer instance
            
        Raises:
            PluginNotFoundError: If analyzer not found
            PluginValidationError: If analyzer invalid
        """
        if not self._auto_discovered:
            self._auto_discover_plugins()
        
        if name not in self._analyzers:
            available = list(self._analyzers.keys())
            raise PluginNotFoundError(
                f"Analyzer '{name}' not found. Available analyzers: {available}. "
                f"Check that the plugin is installed and properly registered."
            )
        
        analyzer_class = self._analyzers[name]
        
        try:
            return analyzer_class(**kwargs)
        except Exception as e:
            raise PluginValidationError(
                f"Failed to create analyzer '{name}': {e}"
            ) from e
    
    def list_analyzers(self) -> List[str]:
        """List all registered analyzer names."""
        if not self._auto_discovered:
            self._auto_discover_plugins()
        return list(self._analyzers.keys())
    
    def _validate_analyzer_class(self, cls: Type[Analyzer], name: str) -> None:
        """Validate that class implements Analyzer interface correctly."""
        if not inspect.isclass(cls):
            raise PluginValidationError(f"Analyzer '{name}' must be a class")
        
        if not issubclass(cls, Analyzer):
            raise PluginValidationError(
                f"Analyzer '{name}' must inherit from Analyzer base class"
            )
        
        # Check required abstract methods are implemented
        required_methods = ["analyze", "name"]
        for method in required_methods:
            if not hasattr(cls, method):
                raise PluginValidationError(
                    f"Analyzer '{name}' missing required method: {method}"
                )
    
    def _auto_discover_plugins(self) -> None:
        """Auto-discover plugins from analyzers/ directory."""
        try:
            # Look for analyzers/ directory relative to current working directory
            analyzers_dir = Path.cwd() / "analyzers"
            if analyzers_dir.exists() and analyzers_dir.is_dir():
                self._scan_directory(analyzers_dir)
            
            # Also check for analyzers in the current Python path
            for path in sys.path:
                path_obj = Path(path)
                analyzers_path = path_obj / "analyzers"
                if analyzers_path.exists() and analyzers_path.is_dir():
                    self._scan_directory(analyzers_path)
        
        except Exception as e:
            logger.warning(f"Plugin auto-discovery failed: {e}")
        finally:
            self._auto_discovered = True
    
    def _scan_directory(self, directory: Path) -> None:
        """Scan directory for Python modules and import them."""
        for py_file in directory.glob("*.py"):
            if py_file.name.startswith("_"):
                continue  # Skip private modules
            
            try:
                module_name = py_file.stem
                spec = importlib.util.spec_from_file_location(module_name, py_file)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[module_name] = module
                    spec.loader.exec_module(module)
                    logger.debug(f"Imported plugin module: {py_file}")
            except Exception as e:
                logger.warning(f"Failed to import plugin {py_file}: {e}")


class PluginNotFoundError(Exception):
    """Raised when a requested plugin analyzer is not found."""
    pass


class PluginValidationError(Exception):
    """Raised when a plugin analyzer fails validation."""
    pass


# Global registry instance
_registry = AnalyzerRegistry()


def register(name: str) -> callable:
    """Global decorator function for analyzer registration."""
    return _registry.register(name)


def get_analyzer(name: str, **kwargs: Any) -> Analyzer:
    """Get analyzer instance by name from global registry."""
    return _registry.get_analyzer(name, **kwargs)


def list_analyzers() -> List[str]:
    """List all registered analyzer names from global registry."""
    return _registry.list_analyzers()