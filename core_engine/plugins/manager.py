"""
Core Engine — Plugin Manager
High-level API for plugin lifecycle: discover, load, configure, and manage.
"""

import os
import sys
import json
import logging
import asyncio
import importlib
from typing import Dict, List, Optional, Any
from pathlib import Path

from .registry import (
    PluginRegistry,
    discover_plugins_in_directory,
    discover_plugins_via_entry_points,
    load_plugin_from_path,
    resolve_load_order,
    PluginLoadResult,
)
from .base import PluginContext, PluginManifest, BasePlugin, PluginCapability

logger = logging.getLogger("hardwareless.plugins.manager")


class PluginManager:
    """
    Facade for plugin system operations.
    Encapsulates discovery, loading, configuration, and health aggregation.
    """
    
    def __init__(
        self,
        plugin_dirs: Optional[List[str]] = None,
        enable_entry_points: bool = True,
        auto_discover: bool = True,
    ):
        self.registry = PluginRegistry()
        self.plugin_dirs = plugin_dirs or ["plugins", "core_engine/plugins"]
        self.enable_entry_points = enable_entry_points
        self.auto_discover = auto_discover
        self._health_cache: Optional[Dict[str, Any]] = None
    
    def discover(self) -> List[PluginManifest]:
        """
        Discover available plugins from all sources.
        Returns list of manifests found (deduplicated by name, highest version wins).
        """
        all_manifests: List[PluginManifest] = []
        
        # 1. Scan configured directories
        for directory in self.plugin_dirs:
            dir_manifests = discover_plugins_in_directory(directory)
            all_manifests.extend(dir_manifests)
        
        # 2. Scan PYTHONPATH for plugin.json in any immediate child dir
        for path_entry in sys.path:
            if not path_entry or not os.path.isdir(path_entry):
                continue
            for item in os.listdir(path_entry):
                p = Path(path_entry) / item
                if p.is_dir() and (p / "plugin.json").exists():
                    try:
                        with open(p / "plugin.json") as f:
                            data = json.load(f)
                        manifest = PluginManifest.from_dict(data)
                        all_manifests.append(manifest)
                    except Exception:
                        pass  # skip invalid
        
        # 3. Entry points
        if self.enable_entry_points:
            eps = discover_plugins_via_entry_points()
            all_manifests.extend(eps)
        
        # Deduplicate by name, keep highest version
        final: Dict[str, PluginManifest] = {}
        for m in all_manifests:
            if m.name not in final or self._compare_versions(m.version, final[m.name].version) > 0:
                final[m.name] = m
        
        logger.info(f"Discovered {len(final)} plugins across {len(all_manifests)} sources")
        return list(final.values())
    
    def _compare_versions(self, v1: str, v2: str) -> int:
        """Simple version compare. Returns 1 if v1 > v2, -1 if <, 0 if equal."""
        def parse(v):
            return [int(x) for x in v.split(".")[:3]]
        p1, p2 = parse(v1), parse(v2)
        for a, b in zip(p1, p2):
            if a > b: return 1
            if a < b: return -1
        return 0
    
    def load_all(self, config: Optional[Dict[str, Any]] = None) -> List[PluginLoadResult]:
        """
        Discover and load all plugins in dependency order.
        Config keyed by plugin name: {"plugin_name": {"config_key": "value"}}
        Returns list of load results (success/failure per plugin).
        """
        results: List[PluginLoadResult] = []
        
        if config is None:
            config = {}
        self.registry.configure(config)
        
        # Discover
        manifests = self.discover()
        
        # Resolve load order
        ordered = resolve_load_order(manifests)
        
        # Load in order
        for manifest in ordered:
            plugin_config = config.get(manifest.name, {})
            
            # Decide whether to load this plugin
            if not plugin_config.get("enabled", manifest.enabled_by_default):
                logger.info(f"Skipping disabled plugin: {manifest.name}")
                continue
            
            # Determine class to load
            if manifest.entry_point:
                try:
                    module_path, class_name = manifest.entry_point.split(":")
                    module = importlib.import_module(module_path)
                    plugin_class = getattr(module, class_name)
                except Exception as e:
                    logger.error(f"Cannot import plugin class for {manifest.name}: {e}")
                    results.append(PluginLoadResult(
                        name=manifest.name, success=False, error=str(e)
                    ))
                    continue
            else:
                logger.warning(f"No entry point for {manifest.name}, skipping")
                continue
            
            result = self.registry.load_plugin(plugin_class, manifest, plugin_config)
            results.append(result)
        
        # Log summary
        success_count = sum(1 for r in results if r.success)
        logger.info(f"Plugin loading complete: {success_count}/{len(results)} succeeded")
        
        return results
    
    def load_from_path(self, path: str, config: Optional[Dict[str, Any]] = None) -> PluginLoadResult:
        """
        Load a single plugin directly from a path (dev mode).
        """
        if config is None:
            config = {}
        
        manifest_path = Path(path) / "plugin.json"
        if not manifest_path.exists():
            return PluginLoadResult(
                name="unknown", success=False, error="No plugin.json in path"
            )
        
        with open(manifest_path) as f:
            data = json.load(f)
        manifest = PluginManifest.from_dict(data)
        
        return load_plugin_from_path(path, manifest, config)
    
    def get_plugin(self, name: str) -> Optional[BasePlugin]:
        """Retrieve loaded plugin by name."""
        return self.registry.get_plugin(name)
    
    def require_plugin(self, name: str) -> BasePlugin:
        """Get plugin or raise if not loaded."""
        p = self.registry.get_plugin(name)
        if p is None:
            raise RuntimeError(f"Plugin '{name}' is not loaded")
        return p
    
    def get_plugins_by_capability(self, capability: PluginCapability) -> List[BasePlugin]:
        """Get all active plugins with a given capability."""
        return self.registry.get_plugins_by_capability(capability)
    
    async def shutdown(self) -> None:
        """Gracefully shut down all plugins."""
        await self.registry.shutdown_all()
    
    def aggregate_health(self) -> Dict[str, Any]:
        """
        Aggregate health status across all active plugins.
        Returns nested dict: {plugin_name: {state: ..., healthy: bool, ...}}
        """
        health = {}
        for name, plugin in self._registry._plugins.items():
            try:
                h = plugin.health_check()
                if isinstance(h, dict):
                    health[name] = h
                else:
                    # Fallback if plugin returns non-dict
                    health[name] = {"plugin": name, "state": plugin.state.value, "healthy": plugin.is_active}
            except Exception as e:
                health[name] = {
                    "plugin": name,
                    "state": "error",
                    "healthy": False,
                    "error": str(e),
                }
        
        # Compute overall
        active_count = sum(1 for v in health.values() if v.get("healthy"))
        total_count = len(health)
        
        return {
            "plugins": health,
            "summary": {
                "active": active_count,
                "total": total_count,
                "healthy_ratio": f"{active_count}/{total_count}" if total_count else "0/0"
            }
        }
    
    @property
    def _registry(self) -> PluginRegistry:
        """Internal accessor."""
        return self.registry


# Singleton instance for application-wide use
_global_manager: Optional[PluginManager] = None

def get_plugin_manager() -> PluginManager:
    """Get or create the global plugin manager."""
    global _global_manager
    if _global_manager is None:
        _global_manager = PluginManager()
    return _global_manager
