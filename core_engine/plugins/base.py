"""
Core Engine — Plugin System Base Classes
Defines plugin interfaces, lifecycle hooks, and manifest schema.
All plugins must inherit from BasePlugin and implement required hooks.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Type
from enum import Enum
import json


class PluginCapability(Enum):
    """Capabilities a plugin can declare."""
    TRANSLATION = "translation"
    COMPRESSION = "compression"
    SECURITY = "security"
    STORAGE = "storage"
    CACHING = "caching"
    OBSERVABILITY = "observability"
    NETWORK = "network"


class PluginPriority(Enum):
    """Priority ordering for plugin loading/execution."""
    CRITICAL = 100  # Core system plugins (must load first)
    HIGH = 80       # Security, compression
    MEDIUM = 50     # Translation backends
    LOW = 20        # Analytics, optional features
    DEV = 0         # Development/debug only


@dataclass
class PluginManifest:
    """
    Declarative plugin manifest — declares what the plugin does and needs.
    Stored as `plugin.json` in plugin directory or package metadata.
    """
    # Identity
    name: str
    version: str
    description: str
    author: str
    
    # Registration
    entry_point: str  # "module.path:ClassName"
    capabilities: List[PluginCapability] = field(default_factory=list)
    priority: PluginPriority = PluginPriority.MEDIUM
    
    # Dependencies
    dependencies: List[str] = field(default_factory=list)  # other plugin names
    conflicts: List[str] = field(default_factory=list)    # incompatible plugins
    
    # Configuration schema (JSON Schema draft-07)
    config_schema: Optional[Dict[str, Any]] = None
    
    # Resource bounds
    max_memory_mb: Optional[int] = None
    max_cpu_percent: Optional[int] = None
    
    # Feature flags
    enabled_by_default: bool = True
    production_ready: bool = False
    
    # Metadata
    tags: List[str] = field(default_factory=list)
    homepage: Optional[str] = None
    repository: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for serialization."""
        d = asdict(self)
        d["capabilities"] = [c.value for c in self.capabilities]
        d["priority"] = self.priority.value
        return d
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PluginManifest":
        """Load from dict."""
        # Convert string caps to enum
        caps = [PluginCapability(c) if isinstance(c, str) else c for c in data.get("capabilities", [])]
        priority = PluginPriority(data.get("priority", PluginPriority.MEDIUM.value))
        data["capabilities"] = caps
        data["priority"] = priority
        return cls(**data)


class PluginState(Enum):
    """Lifecycle states a plugin can be in."""
    UNLOADED = "unloaded"
    LOADING = "loading"
    ACTIVE = "active"
    PAUSED = "paused"
    FAILED = "failed"
    DISABLED = "disabled"


@dataclass
class PluginContext:
    """
    Runtime context provided to plugins.
    Gives access to shared services (config, logging, metrics, other plugins).
    """
    # Plugin system itself
    registry: "PluginRegistry"
    
    # Configuration snapshot (read-only view)
    config: Dict[str, Any]
    
    # Logger for this plugin (pre-configured with plugin name)
    logger: Any  # logging.Logger
    
    # Metrics collector (if observability plugin loaded)
    metrics: Optional[Any] = None
    
    # Shared resource pools
    connection_pool: Optional[Any] = None
    cache: Optional[Any] = None
    
    # Access to other plugins (by name)
    def get_plugin(self, name: str) -> Optional["BasePlugin"]:
        """Get another loaded plugin by name."""
        return self.registry.get_plugin(name)
    
    def require_plugin(self, name: str) -> "BasePlugin":
        """Get another plugin or raise if not loaded."""
        p = self.registry.get_plugin(name)
        if p is None:
            raise RuntimeError(f"Required plugin '{name}' is not loaded")
        return p


class BasePlugin(ABC):
    """
    Abstract base class for all plugins.
    Plugins are instantiated once and may be singleton or scoped.
    """
    
    # Class-level metadata (overridden by subclass)
    manifest: PluginManifest
    
    def __init__(self, context: PluginContext):
        """
        Constructor called during plugin load.
        Plugins should NOT start heavy work here — use `initialize()` instead.
        """
        self.context = context
        self.logger = context.logger
        self.state = PluginState.LOADING
        self._config = self._merge_config()
    
    def _merge_config(self) -> Dict[str, Any]:
        """Merge plugin defaults with global config for this plugin."""
        # Global config keyed by plugin name
        global_cfg = self.context.config.get(self.manifest.name, {})
        # Plugin can also provide defaults via `get_default_config()`
        defaults = self.get_default_config()
        return {**defaults, **global_cfg}
    
    @abstractmethod
    def get_default_config(self) -> Dict[str, Any]:
        """Return default configuration values for this plugin."""
        pass
    
    @abstractmethod
    async def initialize(self) -> None:
        """
        Heavy initialization: connect to services, load models, warm caches.
        Called once after construction. May be async.
        """
        pass
    
    @abstractmethod
    async def shutdown(self) -> None:
        """
        Graceful teardown: close connections, flush buffers, save state.
        Called during application shutdown or plugin unload.
        """
        pass
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Return health status for this plugin.
        Used by the health aggregator to report subsystem status.
        """
        return {
            "plugin": self.manifest.name,
            "state": self.state.value,
            "healthy": self.state == PluginState.ACTIVE,
        }
    
    def get_info(self) -> Dict[str, Any]:
        """Expose plugin metadata and capabilities."""
        return {
            "manifest": self.manifest.to_dict(),
            "state": self.state.value,
            "config": self._config,
        }
    
    # Lifecycle helpers
    def set_active(self):
        """Mark plugin as fully operational."""
        self.state = PluginState.ACTIVE
    
    def set_failed(self, error: Exception):
        """Mark plugin as failed with error context."""
        self.state = PluginState.FAILED
        self.logger.error(f"Plugin failed: {error}", exc_info=error)
    
    def set_paused(self):
        """Temporarily disable without unloading."""
        self.state = PluginState.PAUSED
    
    def set_disabled(self):
        """Explicitly disabled by config/operator."""
        self.state = PluginState.DISABLED
    
    @property
    def is_active(self) -> bool:
        return self.state == PluginState.ACTIVE
    
    @property
    def config(self) -> Dict[str, Any]:
        """Read-only access to merged configuration."""
        return self._config.copy()


# Type alias for plugin class
PluginClass = Type[BasePlugin]
