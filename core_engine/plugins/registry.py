"""
Core Engine — Plugin Registry
Singleton registry for discovering, loading, and managing plugins.
Supports multiple loading mechanisms: directory scanning, entry points, config.
"""

import os
import sys
import json
import importlib
import importlib.metadata
import inspect
import logging
from typing import Dict, List, Optional, Any, Set
from pathlib import Path
from dataclasses import dataclass, field

from .base import (
    BasePlugin,
    PluginManifest,
    PluginContext,
    PluginState,
    PluginCapability,
    PluginPriority,
)


logger = logging.getLogger("hardwareless.plugins")


@dataclass
class PluginLoadResult:
    """Result of a plugin load attempt."""
    name: str
    success: bool
    plugin: Optional[BasePlugin] = None
    error: Optional[str] = None
    dependencies_missing: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class PluginRegistry:
    """
    Singleton registry managing plugin lifecycle.
    Central hub for plugin discovery, loading, and access.
    """
    
    def __init__(self):
        self._plugins: Dict[str, BasePlugin] = {}
        self._manifests: Dict[str, PluginManifest] = {}
        self._load_order: List[str] = []
        self._config: Dict[str, Any] = {}
        self._initialized = False
    
    def register_manifest(self, manifest: PluginManifest) -> None:
        """Register a plugin manifest (discovery phase)."""
        self._manifests[manifest.name] = manifest
        logger.debug(f"Registered plugin manifest: {manifest.name} v{manifest.version}")
    
    def load_plugin(self, plugin_class: type, manifest: PluginManifest, config: Dict[str, Any]) -> PluginLoadResult:
        """
        Instantiate and initialize a plugin.
        Returns load result with success/error details.
        """
        result = PluginLoadResult(name=manifest.name, success=False)
        
        try:
            # Create plugin context
            ctx = PluginContext(
                registry=self,
                config=config,
                logger=logging.getLogger(f"hardwareless.plugins.{manifest.name}"),
            )
            
            # Instantiate
            plugin = plugin_class(ctx)
            result.plugin = plugin
            
            # Check dependencies
            missing = self._check_dependencies(manifest)
            if missing:
                result.dependencies_missing = missing
                result.error = f"Missing dependencies: {', '.join(missing)}"
                plugin.set_failed(RuntimeError(result.error))
                return result
            
            # Call async initialize
            import asyncio
            loop = asyncio.get_event_loop()
            loop.run_until_complete(plugin.initialize())
            
            plugin.set_active()
            self._plugins[manifest.name] = plugin
            self._load_order.append(manifest.name)
            
            result.success = True
            logger.info(f"Plugin loaded: {manifest.name} v{manifest.version} (state={plugin.state.value})")
            
        except Exception as e:
            result.error = str(e)
            logger.error(f"Failed to load plugin {manifest.name}: {e}", exc_info=True)
        
        return result
    
    def _check_dependencies(self, manifest: PluginManifest) -> List[str]:
        """Verify all declared dependencies are loaded and active."""
        missing = []
        for dep in manifest.dependencies:
            if dep not in self._plugins:
                missing.append(dep)
            elif not self._plugins[dep].is_active:
                missing.append(f"{dep} (loaded but not active)")
        return missing
    
    def get_plugin(self, name: str) -> Optional[BasePlugin]:
        """Retrieve a loaded plugin by name."""
        return self._plugins.get(name)
    
    def get_plugins_by_capability(self, capability: PluginCapability) -> List[BasePlugin]:
        """Get all active plugins that declare a capability."""
        return [
            p for p in self._plugins.values()
            if p.is_active and capability in p.manifest.capabilities
        ]
    
    def get_load_order(self) -> List[str]:
        """Return plugins in dependency-resolved load order."""
        return self._load_order.copy()
    
    def get_all_manifests(self) -> Dict[str, PluginManifest]:
        """Return all discovered manifests (before loading)."""
        return self._manifests.copy()
    
    async def shutdown_all(self) -> None:
        """Gracefully shut down all plugins in reverse load order."""
        for name in reversed(self._load_order):
            plugin = self._plugins.get(name)
            if plugin and plugin.is_active:
                try:
                    await plugin.shutdown()
                    plugin.set_disabled()
                    logger.info(f"Plugin shut down: {name}")
                except Exception as e:
                    logger.error(f"Error shutting down plugin {name}: {e}")
    
    def configure(self, config: Dict[str, Any]) -> None:
        """Set global plugin configuration before loading."""
        self._config = config
    
    def is_loaded(self, name: str) -> bool:
        """Check if a plugin is loaded and active."""
        return name in self._plugins and self._plugins[name].is_active


# Singleton instance
_registry = PluginRegistry()

def get_registry() -> PluginRegistry:
    """Access the global plugin registry."""
    return _registry


# ——————————————————————————————
# Plugin Discovery
# ——————————————————————————————

def discover_plugins_in_directory(directory: str) -> List[PluginManifest]:
    """
    Scan a directory for plugin directories containing plugin.json.
    Returns list of discovered manifests.
    """
    discovered = []
    search_path = Path(directory)
    
    if not search_path.exists():
        logger.warning(f"Plugin directory not found: {directory}")
        return discovered
    
    for plugin_dir in search_path.iterdir():
        if not plugin_dir.is_dir():
            continue
        
        manifest_path = plugin_dir / "plugin.json"
        if not manifest_path.exists():
            continue
        
        try:
            with open(manifest_path) as f:
                data = json.load(f)
            manifest = PluginManifest.from_dict(data)
            discovered.append(manifest)
            logger.info(f"Discovered plugin: {manifest.name} v{manifest.version} at {plugin_dir}")
        except Exception as e:
            logger.error(f"Failed to parse plugin manifest at {manifest_path}: {e}")
    
    return discovered


def discover_plugins_via_entry_points() -> List[PluginManifest]:
    """
    Discover plugins registered via setuptools entry points (installed packages).
    Entry point group: 'hardwareless.plugins'
    """
    discovered = []
    
    try:
        eps = importlib.metadata.entry_points()
        # Python 3.10+ returns dict, older return list
        if hasattr(eps, 'select'):
            group_eps = eps.select(group='hardwareless.plugins')
        else:
            group_eps = [ep for ep in eps if ep.group == 'hardwareless.plugins']
        
        for ep in group_eps:
            try:
                # ep.value is "module.path:ClassName"
                module_path, class_name = ep.value.split(":")
                module = importlib.import_module(module_path)
                plugin_class = getattr(module, class_name)
                
                # Plugin class must have `manifest` attribute
                if hasattr(plugin_class, 'manifest'):
                    manifest = plugin_class.manifest
                    discovered.append(manifest)
                    logger.info(f"Discovered plugin via entry point: {manifest.name} v{manifest.version}")
            except Exception as e:
                logger.error(f"Entry point discovery failed for {ep.name}: {e}")
                
    except Exception as e:
        logger.warning(f"Entry point discovery unavailable: {e}")
    
    return discovered


def load_plugin_from_path(plugin_path: str, manifest: PluginManifest, config: Dict[str, Any]) -> PluginLoadResult:
    """
    Load a plugin from a filesystem path (editable development mode).
    Adds the plugin directory to sys.path and imports the class.
    """
    result = PluginLoadResult(name=manifest.name, success=False)
    
    try:
        plugin_dir = Path(plugin_path).resolve()
        sys.path.insert(0, str(plugin_dir.parent))
        
        module_path = manifest.entry_point.split(":")[0]
        class_name = manifest.entry_point.split(":")[1] if ":" in manifest.entry_point else None
        
        module = importlib.import_module(module_path)
        plugin_class = getattr(module, class_name) if class_name else module
        
        # Must be subclass of BasePlugin
        if not inspect.isclass(plugin_class) or not issubclass(plugin_class, BasePlugin):
            raise TypeError(f"{plugin_class} is not a BasePlugin subclass")
        
        result = load_plugin(plugin_class, manifest, config)
        
    except Exception as e:
        result.error = str(e)
        logger.error(f"Failed to load plugin from path {plugin_path}: {e}")
    
    return result


def load_plugin(plugin_class: type, manifest: PluginManifest, config: Dict[str, Any]) -> PluginLoadResult:
    """Delegate to registry (internal API)."""
    return _registry.load_plugin(plugin_class, manifest, config)


# ——————————————————————————————
# Dependency Resolution (simple topological sort)
# ——————————————————————————————

def resolve_load_order(manifests: List[PluginManifest]) -> List[PluginManifest]:
    """
    Order manifests by priority and dependencies.
    Returns list in safe load order (dependencies before dependents).
    """
    name_to_manifest = {m.name: m for m in manifests}
    resolved: List[str] = []
    visiting: Set[str] = set()
    
    def visit(name: str) -> None:
        if name in resolved:
            return
        if name in visiting:
            raise RuntimeError(f"Circular plugin dependency detected: {name}")
        if name not in name_to_manifest:
            raise RuntimeError(f"Missing plugin dependency: {name}")
        
        visiting.add(name)
        manifest = name_to_manifest[name]
        
        # Visit dependencies first
        for dep in manifest.dependencies:
            visit(dep)
        
        visiting.remove(name)
        resolved.append(name)
    
    # Sort by priority first, then topological
    priority_sorted = sorted(manifests, key=lambda m: m.priority.value, reverse=True)
    
    for manifest in priority_sorted:
        visit(manifest.name)
    
    return [name_to_manifest[n] for n in resolved]
