"""Plugin registry system for GeoExhibit analyzers."""

import importlib
import importlib.util
import logging
from pathlib import Path
from typing import Dict, Type, Optional, Set, Any
import inspect

from .analyzer import Analyzer

logger = logging.getLogger(__name__)


class PluginRegistry:
    """Registry for analyzer plugins with decorator-based registration."""
    
    def __init__(self) -> None:
        self._analyzers: Dict[str, Type[Analyzer]] = {}
        self._discovered_directories: Set[Path] = set()
    
    def register(self, name: str) -> Any:
        """Decorator to register an analyzer plugin.
        
        Args:
            name: Name to register the analyzer under
            
        Returns:
            Decorator function
            
        Example:
            @analyzer.register("my_analyzer")
            class MyAnalyzer(Analyzer):
                ...
        """
        def decorator(analyzer_class: Type[Analyzer]) -> Type[Analyzer]:
            if not issubclass(analyzer_class, Analyzer):
                raise ValueError(
                    f"Plugin {name} must inherit from Analyzer interface. "
                    f"Class {analyzer_class.__name__} does not implement required methods."
                )
            
            if name in self._analyzers:
                logger.warning(f"Analyzer '{name}' is already registered, overwriting")
            
            self._analyzers[name] = analyzer_class
            logger.debug(f"Registered analyzer plugin: {name}")
            
            return analyzer_class
        
        return decorator
    
    def get_analyzer(self, name: str) -> Optional[Type[Analyzer]]:
        """Get an analyzer class by name.
        
        Args:
            name: Name of the analyzer to retrieve
            
        Returns:
            Analyzer class if found, None otherwise
        """
        return self._analyzers.get(name)
    
    def list_analyzers(self) -> Dict[str, Type[Analyzer]]:
        """Get all registered analyzers.
        
        Returns:
            Dictionary of analyzer name to class mappings
        """
        return self._analyzers.copy()
    
    def discover_plugins(self, directory: Path) -> None:
        """Auto-discover plugins from a directory by scanning .py files.
        
        Args:
            directory: Directory to scan for plugin files
        """
        if not directory.exists() or not directory.is_dir():
            logger.debug(f"Plugin directory {directory} does not exist, skipping")
            return
        
        if directory in self._discovered_directories:
            logger.debug(f"Directory {directory} already discovered, skipping")
            return
        
        logger.debug(f"Discovering plugins in {directory}")
        
        python_files = list(directory.glob("*.py"))
        if not python_files:
            logger.debug(f"No Python files found in {directory}")
            return
        
        for py_file in python_files:
            if py_file.name.startswith("_"):
                continue  # Skip private modules
            
            try:
                self._load_plugin_module(py_file)
            except Exception as e:
                logger.error(f"Failed to load plugin from {py_file}: {e}")
        
        self._discovered_directories.add(directory)
    
    def _load_plugin_module(self, module_path: Path) -> None:
        """Load a plugin module and trigger any @register decorators.
        
        Args:
            module_path: Path to the Python module to load
        """
        module_name = f"geoexhibit_plugin_{module_path.stem}"
        
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load module spec from {module_path}")
        
        module = importlib.util.module_from_spec(spec)
        
        try:
            spec.loader.exec_module(module)
            logger.debug(f"Successfully loaded plugin module {module_name}")
        except Exception as e:
            raise ImportError(f"Failed to execute plugin module {module_path}: {e}")
    
    def validate_plugin(self, analyzer_class: Type[Any]) -> None:
        """Validate that a plugin class properly implements the Analyzer interface.
        
        Args:
            analyzer_class: Class to validate
            
        Raises:
            ValueError: If the class doesn't properly implement the interface
        """
        if not issubclass(analyzer_class, Analyzer):
            raise ValueError(
                f"Plugin {analyzer_class.__name__} must inherit from Analyzer"
            )
        
        # Check required methods
        required_methods = ["analyze", "name"]
        for method_name in required_methods:
            if not hasattr(analyzer_class, method_name):
                raise ValueError(
                    f"Plugin {analyzer_class.__name__} missing required method: {method_name}"
                )
            
            method = getattr(analyzer_class, method_name)
            if method_name == "analyze" and not callable(method):
                raise ValueError(
                    f"Plugin {analyzer_class.__name__}.{method_name} must be callable"
                )
        
        # Check analyze method signature
        try:
            sig = inspect.signature(analyzer_class.analyze)
            params = list(sig.parameters.keys())
            # Should have self, feature, timespan parameters
            if len(params) < 3 or params[1] != "feature" or params[2] != "timespan":
                raise ValueError(
                    f"Plugin {analyzer_class.__name__}.analyze must have signature "
                    f"(self, feature, timespan), got {params}"
                )
        except (TypeError, AttributeError) as e:
            raise ValueError(
                f"Cannot inspect analyze method signature for {analyzer_class.__name__}: {e}"
            )
    
    def create_analyzer(self, name: str, **kwargs: Any) -> Analyzer:
        """Create an instance of the named analyzer.
        
        Args:
            name: Name of the analyzer to create
            **kwargs: Arguments to pass to the analyzer constructor
            
        Returns:
            Analyzer instance
            
        Raises:
            ValueError: If analyzer not found or cannot be instantiated
        """
        analyzer_class = self.get_analyzer(name)
        if analyzer_class is None:
            available = list(self._analyzers.keys())
            raise ValueError(
                f"Analyzer '{name}' not found. Available analyzers: {available}. "
                f"Ensure the plugin is installed and discoverable."
            )
        
        try:
            return analyzer_class(**kwargs)
        except Exception as e:
            raise ValueError(
                f"Failed to create analyzer '{name}': {e}. "
                f"Check the analyzer's constructor requirements."
            )


# Global registry instance
_registry = PluginRegistry()

# Export the main decorator for easy importing
def register(name: str) -> Any:
    """Register an analyzer plugin.
    
    This is a convenience function that delegates to the global registry.
    
    Args:
        name: Name to register the analyzer under
        
    Returns:
        Decorator function
        
    Example:
        from geoexhibit.plugin_registry import register
        
        @register("my_analyzer")
        class MyAnalyzer(Analyzer):
            ...
    """
    return _registry.register(name)


def get_registry() -> PluginRegistry:
    """Get the global plugin registry instance."""
    return _registry