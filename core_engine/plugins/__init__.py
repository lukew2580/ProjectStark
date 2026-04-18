"""
Core Engine — Plugin Package
Plugin system for extensible, hot-swappable components.
"""

from .base import (
    BasePlugin,
    PluginManifest,
    PluginContext,
    PluginState,
    PluginCapability,
    PluginPriority,
)
from .registry import (
    PluginRegistry,
    get_registry,
    discover_plugins_in_directory,
    discover_plugins_via_entry_points,
    resolve_load_order,
)
from .manager import (
    PluginManager,
    get_plugin_manager,
    PluginLoadResult,
)

__all__ = [
    # Base classes
    "BasePlugin",
    "PluginManifest",
    "PluginContext",
    "PluginState",
    "PluginCapability",
    "PluginPriority",
    
    # Registry
    "PluginRegistry",
    "get_registry",
    "discover_plugins_in_directory",
    "discover_plugins_via_entry_points",
    "resolve_load_order",
    
    # Manager
    "PluginManager",
    "get_plugin_manager",
    "PluginLoadResult",
]
