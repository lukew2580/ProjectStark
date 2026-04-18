"""
Core Engine — Plugin Specializations
Domain-specific base classes for common plugin patterns.
"""

from typing import Dict, List, Optional, Any, Tuple
from abc import abstractmethod

from .base import BasePlugin, PluginContext, PluginManifest, PluginCapability, PluginPriority


class TranslatorBackendPlugin(BasePlugin):
    """
    Base for translation backend plugins.
    Wraps existing translation backends (MTranServer, LibreTranslate, OpusMT)
    as first-class plugins.
    """
    
    def __init__(self, context: PluginContext):
        super().__init__(context)
        self.backend: Optional[Any] = None
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the translation backend (load models, connect server, etc.)."""
        pass
    
    @abstractmethod
    async def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        **options: Any
    ) -> Tuple[str, float]:
        """
        Translate text. Returns (translated_text, confidence).
        Confidence is 0.0-1.0.
        """
        pass
    
    @abstractmethod
    async def detect_language(self, text: str) -> Tuple[str, float]:
        """
        Detect language of text. Returns (lang_code, confidence).
        """
        pass
    
    @abstractmethod
    async def list_supported_languages(self) -> List[str]:
        """List language codes this backend supports."""
        pass
    
    async def shutdown(self) -> None:
        """Gracefully shutdown backend (close connections, free GPU memory)."""
        self.backend = None
        self.set_disabled()
    
    def get_default_config(self) -> Dict[str, Any]:
        return {
            "enabled": True,
            "priority": 10,
            "timeout_seconds": 30,
        }
    
    def health_check(self) -> Dict[str, Any]:
        base = super().health_check()
        # Add backend-specific health (if backend has health_check method)
        if self.backend and hasattr(self.backend, 'health_check'):
            try:
                base["backend"] = self.backend.health_check()
            except Exception:
                base["backend"] = {"status": "unavailable"}
        return base


class CompressionPlugin(BasePlugin):
    """
    Base for cognitive compression plugins.
    Compresses natural language to dense semantic representation.
    """
    
    def __init__(self, context: PluginContext):
        super().__init__(context)
        self.compressor: Optional[Any] = None
    
    @abstractmethod
    async def compress(self, text: str, **options: Any) -> str:
        """
        Compress text to HDC vector space.
        Returns compressed representation (string or base64-encoded vector).
        """
        pass
    
    @abstractmethod
    async def decompress(self, compressed: str, **options: Any) -> str:
        """Decompress representation back to text (best effort)."""
        pass
    
    def get_default_config(self) -> Dict[str, Any]:
        return {
            "enabled": True,
            "priority": 5,
            "min_length_to_compress": 50,
        }
    
    async def shutdown(self) -> None:
        self.compressor = None
        self.set_disabled()


class CachePlugin(BasePlugin):
    """
    Base for caching backends.
    Supports request caching, vector caching, knowledge base caching.
    """
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Retrieve value from cache."""
        pass
    
    @abstractmethod
    async def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
        """Store value in cache with optional TTL."""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Remove key from cache."""
        pass
    
    @abstractmethod
    async def clear(self) -> int:
        """Clear all keys. Returns count removed."""
        pass
    
    @abstractmethod
    async def stats(self) -> Dict[str, Any]:
        """Return cache statistics (hits, misses, size)."""
        pass
    
    def get_default_config(self) -> Dict[str, Any]:
        return {
            "enabled": True,
            "priority": 2,
            "default_ttl_seconds": 3600,
            "max_size": 10000,
        }
    
    async def health_check(self) -> Dict[str, Any]:
        base = super().health_check()
        try:
            stats = await self.stats()
            base["stats"] = stats
        except Exception as e:
            base["stats_error"] = str(e)
        return base


class ObservabilityPlugin(BasePlugin):
    """
    Base for observability integrations.
    Provides metrics, tracing, logging aggregation.
    """
    
    @abstractmethod
    def increment_counter(self, name: str, value: int = 1, tags: Optional[Dict[str, str]] = None) -> None:
        """Increment a counter metric."""
        pass
    
    @abstractmethod
    def record_gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Record a gauge metric."""
        pass
    
    @abstractmethod
    def record_histogram(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Record a histogram value (latency, size)."""
        pass
    
    @abstractmethod
    def start_span(self, name: str, **attrs: Any):
        """Start a tracing span. Returns context manager."""
        pass
    
    def get_default_config(self) -> Dict[str, Any]:
        return {
            "enabled": True,
            "priority": 3,
            "export_interval_seconds": 10,
        }
    
    async def shutdown(self) -> None:
        # Flush any pending metrics
        await super().shutdown()


class SecurityPlugin(BasePlugin):
    """
    Base for security plugins.
    Input validation, threat detection, audit logging, anomaly detection.
    """
    
    @abstractmethod
    async def validate_request(self, request_data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validate a request. Returns (is_valid, error_message).
        Called early in request pipeline.
        """
        pass
    
    @abstractmethod
    async def audit_event(self, event_type: str, details: Dict[str, Any], level: str = "info") -> None:
        """Record a security audit event."""
        pass
    
    @abstractmethod
    async def check_anomaly(self, request_data: Dict[str, Any], historical: List[Dict[str, Any]]) -> Optional[str]:
        """
        Check if request is anomalous.
        Returns anomaly description or None.
        """
        pass
    
    def get_default_config(self) -> Dict[str, Any]:
        return {
            "enabled": True,
            "priority": 100,  # Security plugins load first (CRITICAL)
            "block_on_failure": True,
            "audit_file": "logs/audit.jsonl",
        }
    
    async def shutdown(self) -> None:
        # Ensure audit log flushed
        await super().shutdown()


# Convenience: create manifest helper
def create_plugin_manifest(
    name: str,
    version: str,
    description: str,
    author: str,
    entry_point: str,
    capabilities: Optional[List[PluginCapability]] = None,
    priority: PluginPriority = PluginPriority.MEDIUM,
    **kwargs: Any,
) -> PluginManifest:
    """Factory for plugin manifests with sensible defaults."""
    return PluginManifest(
        name=name,
        version=version,
        description=description,
        author=author,
        entry_point=entry_point,
        capabilities=capabilities or [],
        priority=priority,
        **kwargs,
    )


__all__ = [
    # Specialized bases
    "TranslatorBackendPlugin",
    "CompressionPlugin",
    "CachePlugin",
    "ObservabilityPlugin",
    "SecurityPlugin",
    # Helper
    "create_plugin_manifest",
]
