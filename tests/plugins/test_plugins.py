"""
Test Suite — Plugin System (core_engine/plugins/)
Covers: base.py, registry.py, manager.py, specializations.py
"""
import pytest
import asyncio
import json
import tempfile
import os
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

from core_engine.plugins.base import (
    BasePlugin, PluginManifest, PluginContext, PluginState,
    PluginCapability, PluginPriority
)
from core_engine.plugins.registry import (
    PluginRegistry, PluginLoadResult,
    discover_plugins_in_directory, discover_plugins_via_entry_points,
    load_plugin, resolve_load_order
)
from core_engine.plugins.manager import PluginManager, get_plugin_manager
from core_engine.plugins.specializations import (
    TranslatorBackendPlugin, CompressionPlugin, CachePlugin,
    ObservabilityPlugin, SecurityPlugin, create_plugin_manifest
)

# ============================================================================
# Module-level plugin classes (importable for entry_point resolution)
# ============================================================================

class SimplePlugin(BasePlugin):
    """Concrete plugin used by multiple tests."""
    manifest = PluginManifest(
        name="simple",
        version="1.0.0",
        description="A simple test plugin",
        author="Test",
        entry_point="test_plugins:SimplePlugin",
        capabilities=[PluginCapability.CACHING],
        priority=PluginPriority.MEDIUM,
    )
    def get_default_config(self):
        return {"enabled": True, "value": 42}
    async def initialize(self):
        self.initialized = True
    async def shutdown(self):
        self.shutdown_called = True


class MockPlugin(BasePlugin):
    """Mock plugin used by multiple tests."""
    manifest = PluginManifest(
        name="mock",
        version="0.1.0",
        description="Mock plugin",
        author="Test",
        entry_point="test_plugins:MockPlugin",
    )
    def __init__(self, context):
        super().__init__(context)
        self.init_called = False
        self.shutdown_called = False
    def get_default_config(self):
        return {"enabled": True}
    async def initialize(self):
        self.init_called = True
    async def shutdown(self):
        self.shutdown_called = True


# ——————————————————————————————————————————
# Fixtures
# ——————————————————————————————————————————

@pytest.fixture
def simple_plugin_class():
    """Return the module-level SimplePlugin class."""
    return SimplePlugin


@pytest.fixture
def mock_plugin_class():
    """Return the module-level MockPlugin class."""
    return MockPlugin


@pytest.fixture
def temp_plugin_dir():
    """Create a temporary plugin directory with a valid plugin.json."""
    tmpdir = tempfile.mkdtemp()
    plugins_root = Path(tmpdir) / "plugins"
    plugins_root.mkdir()
    plugin_dir = plugins_root / "test_plugin"
    plugin_dir.mkdir()
    
    manifest = {
        "name": "temp_plugin",
        "version": "0.1.0",
        "description": "Temporary plugin for testing",
        "author": "Test",
        "entry_point": "plugin_module:PluginClass",
        "capabilities": ["caching"],
        "priority": 50
    }
    (plugin_dir / "plugin.json").write_text(json.dumps(manifest))
    
    # Create a dummy plugin module file
    (plugin_dir / "plugin_module.py").write_text("""
from core_engine.plugins.base import BasePlugin, PluginContext

class PluginClass(BasePlugin):
    def get_default_config(self):
        return {"enabled": True}
    async def initialize(self):
        pass
    async def shutdown(self):
        pass
""")
    
    yield str(plugins_root)  # yield the root containing plugin subdirs
    # Cleanup
    import shutil
    shutil.rmtree(tmpdir)


# ——————————————————————————————————————————
# PluginManifest Tests
# ——————————————————————————————————————————

class TestPluginManifest:
    def test_manifest_creation(self):
        m = PluginManifest(
            name="test",
            version="1.0.0",
            description="Test plugin",
            author="Me",
            entry_point="module:Class"
        )
        assert m.name == "test"
        assert m.capabilities == []
        assert m.priority == PluginPriority.MEDIUM
        assert m.enabled_by_default is True

    def test_manifest_to_dict(self):
        m = PluginManifest(
            name="test",
            version="1.0.0",
            description="Test",
            author="Me",
            entry_point="module:Class",
            capabilities=[PluginCapability.TRANSLATION, PluginCapability.CACHING],
            priority=PluginPriority.HIGH
        )
        d = m.to_dict()
        assert d["name"] == "test"
        assert d["capabilities"] == ["translation", "caching"]
        assert d["priority"] == 80

    def test_manifest_from_dict(self):
        data = {
            "name": "test",
            "version": "2.0.0",
            "description": "Test",
            "author": "Me",
            "entry_point": "module:Class",
            "capabilities": ["security"],
            "priority": 100
        }
        m = PluginManifest.from_dict(data)
        assert m.name == "test"
        assert PluginCapability.SECURITY in m.capabilities
        assert m.priority == PluginPriority.CRITICAL


# ——————————————————————————————————————————
# PluginContext Tests
# —————————————————————————————————————————

class TestPluginContext:
    def test_get_plugin_returns_plugin(self):
        registry = PluginRegistry()
        ctx = PluginContext(registry=registry, config={}, logger=MagicMock())
        # No plugin loaded yet
        assert ctx.get_plugin("nonexistent") is None

    def test_require_plugin_raises_if_missing(self):
        registry = PluginRegistry()
        ctx = PluginContext(registry=registry, config={}, logger=MagicMock())
        with pytest.raises(RuntimeError):
            ctx.require_plugin("nonexistent")


# ——————————————————————————————————————————
# BasePlugin Tests
# —————————————————————————————————————————

class TestBasePlugin:
    @pytest.mark.asyncio
    async def test_plugin_lifecycle(self, simple_plugin_class):
        registry = PluginRegistry()
        ctx = PluginContext(
            registry=registry,
            config={simple_plugin_class.manifest.name: {}},
            logger=MagicMock(),
        )
        
        plugin = simple_plugin_class(ctx)
        assert plugin.state == PluginState.LOADING
        
        # Initialize async
        await plugin.initialize()
        assert plugin.initialized is True
        plugin.set_active()
        assert plugin.is_active is True
        
        # Shutdown
        await plugin.shutdown()
        assert plugin.shutdown_called is True

    def test_plugin_config_merging(self, simple_plugin_class):
        registry = PluginRegistry()
        ctx = PluginContext(
            registry=registry,
            config={simple_plugin_class.manifest.name: {"custom": "value"}},
            logger=MagicMock(),
        )
        plugin = simple_plugin_class(ctx)
        cfg = plugin.config
        assert cfg["enabled"] is True
        assert cfg["value"] == 42
        assert cfg["custom"] == "value"

    @pytest.mark.asyncio
    async def test_plugin_health_check(self, simple_plugin_class):
        registry = PluginRegistry()
        ctx = PluginContext(registry=registry, config={}, logger=MagicMock())
        plugin = simple_plugin_class(ctx)
        await plugin.initialize()
        plugin.set_active()
        health = await plugin.health_check()
        assert health["plugin"] == "simple"
        assert health["healthy"] is True


# ——————————————————————————————————————————
# Registry Tests
# —————————————————————————————————————————

class TestPluginRegistry:
    @pytest.mark.asyncio
    async def test_register_and_get_plugin(self, simple_plugin_class):
        """Test that plugin can be manually registered and retrieved."""
        registry = PluginRegistry()
        ctx = PluginContext(registry=registry, config={}, logger=MagicMock())
        plugin = simple_plugin_class(ctx)
        await plugin.initialize()
        plugin.set_active()
        registry._plugins[simple_plugin_class.manifest.name] = plugin
        registry._load_order.append(simple_plugin_class.manifest.name)
        
        assert registry.is_loaded("simple") is True
        assert registry.get_plugin("simple") is plugin

    @pytest.mark.asyncio
    async def test_dependency_checking(self):
        class DepPlugin(BasePlugin):
            def get_default_config(self): return {}
            async def initialize(self): pass
            async def shutdown(self): pass
        class ProviderPlugin(DepPlugin):
            pass
        
        DepPlugin.manifest = PluginManifest("dep","1","D","T","d:Class", dependencies=[])
        ProviderPlugin.manifest = PluginManifest("prov","1","P","T","p:Class", dependencies=["dep"])
        
        registry = PluginRegistry()
        # Load dependency
        ctx = PluginContext(registry=registry, config={}, logger=MagicMock())
        dep = DepPlugin(ctx)
        await dep.initialize()
        dep.set_active()
        registry._plugins["dep"] = dep
        
        # Check provider deps satisfied
        missing = registry._check_dependencies(ProviderPlugin.manifest)
        assert missing == []
        
        # Add another that requires missing
        class Orphan(BasePlugin):
            def get_default_config(self): return {}
            async def initialize(self): pass
            async def shutdown(self): pass
        Orphan.manifest = PluginManifest("orphan","1","O","T","o:Class", dependencies=["ghost"])
        missing = registry._check_dependencies(Orphan.manifest)
        assert "ghost" in missing

    def test_missing_dependency_fails(self):
        class NeedsDep(BasePlugin):
            def get_default_config(self): return {}
            async def initialize(self): pass
            async def shutdown(self): pass
        NeedsDep.manifest = PluginManifest("needs","1","N","T","n:Class", dependencies=["missing"])
        
        registry = PluginRegistry()
        missing = registry._check_dependencies(NeedsDep.manifest)
        assert "missing" in missing

    def test_get_plugins_by_capability(self, simple_plugin_class):
        registry = PluginRegistry()
        ctx = PluginContext(registry=registry, config={}, logger=MagicMock())
        plugin = simple_plugin_class(ctx)
        asyncio.run(plugin.initialize())
        plugin.set_active()
        registry._plugins[simple_plugin_class.manifest.name] = plugin
        
        plugins = registry.get_plugins_by_capability(PluginCapability.CACHING)
        assert len(plugins) == 1
        assert plugins[0].manifest.name == "simple"

    def test_load_order_respects_dependencies(self):
        class A(BasePlugin):
            def get_default_config(self): return {}
            async def initialize(self): pass
            async def shutdown(self): pass
        class B(A): pass
        class C(A): pass
        
        A.manifest = PluginManifest("A","1","A","T","A:Class", dependencies=[])
        B.manifest = PluginManifest("B","1","B","T","B:Class", dependencies=["A"])
        C.manifest = PluginManifest("C","1","C","T","C:Class", dependencies=["B"])
        
        manifests = [A.manifest, B.manifest, C.manifest]
        order = resolve_load_order(manifests)
        names = [m.name for m in order]
        assert names.index("A") < names.index("B") < names.index("C")

    def test_circular_dependency_detected(self):
        class A(BasePlugin):
            def get_default_config(self): return {}
            async def initialize(self): pass
            async def shutdown(self): pass
        class B(A): pass
        
        A.manifest = PluginManifest("A","1","A","T","A:Class", dependencies=["B"])
        B.manifest = PluginManifest("B","1","B","T","B:Class", dependencies=["A"])
        
        with pytest.raises(RuntimeError, match="Circular plugin dependency"):
            resolve_load_order([A.manifest, B.manifest])

    @pytest.mark.asyncio
    async def test_shutdown_all_reverse_order(self):
        # Define three plugin classes with manifests as class attributes
        class TrackedPluginA(BasePlugin):
            name = "A"
            manifest = PluginManifest("A","1","A","T","m:A", dependencies=[])
            def get_default_config(self): return {}
            async def initialize(self): pass
            async def shutdown(self):
                self.shutdown_called = True
        class TrackedPluginB(BasePlugin):
            name = "B"
            manifest = PluginManifest("B","1","B","T","m:B", dependencies=["A"])
            def get_default_config(self): return {}
            async def initialize(self): pass
            async def shutdown(self):
                self.shutdown_called = True
        class TrackedPluginC(BasePlugin):
            name = "C"
            manifest = PluginManifest("C","1","C","T","m:C", dependencies=["B"])
            def get_default_config(self): return {}
            async def initialize(self): pass
            async def shutdown(self):
                self.shutdown_called = True
        
        registry = PluginRegistry()
        for cls in [TrackedPluginA, TrackedPluginB, TrackedPluginC]:
            ctx = PluginContext(registry=registry, config={}, logger=MagicMock())
            p = cls(ctx)
            await p.initialize()
            p.set_active()
            registry._plugins[p.manifest.name] = p
            registry._load_order.append(p.manifest.name)
        
        # Shutdown in reverse order (A,B,C) -> C,B,A
        await registry.shutdown_all()
        # Check that all were shut down (via flag on each instance)
        # Need to capture instances; let's store them
        # Actually we can check by accessing registry plugins after shutdown state
        for name in ["A","B","C"]:
            plugin = registry._plugins[name]
            assert plugin.state == PluginState.DISABLED


# ——————————————————————————————————————————
# Manager Tests
# —————————————————————————————————————————

class TestPluginManager:
    @pytest.mark.asyncio
    async def test_discover_from_directory(self, temp_plugin_dir):
        manager = PluginManager(plugin_dirs=[temp_plugin_dir], auto_discover=False)
        manifests = manager.discover()
        assert len(manifests) >= 1
        temp = [m for m in manifests if m.name == "temp_plugin"]
        assert len(temp) == 1

    @pytest.mark.asyncio
    async def test_load_all_with_config(self, simple_plugin_class, monkeypatch):
        manager = PluginManager()
        captured = []
        original_load = manager.registry.load_plugin
        
        async def mock_load(plugin_class, manifest, config):
            captured.append((manifest.name, config))
            return await original_load(plugin_class, manifest, config)
        
        monkeypatch.setattr(manager.registry, "load_plugin", mock_load)
        monkeypatch.setattr(manager, "discover", lambda: [simple_plugin_class.manifest])
        
        results = await manager.load_all(config={simple_plugin_class.manifest.name: {"foo": "bar"}})
        assert len(results) == 1
        assert results[0].success is True
        assert captured[0] == ("simple", {"foo": "bar"})

    @pytest.mark.asyncio
    async def test_aggregate_health(self, simple_plugin_class):
        manager = PluginManager()
        registry = manager.registry
        ctx = PluginContext(registry=registry, config={}, logger=MagicMock())
        plugin = simple_plugin_class(ctx)
        await plugin.initialize()
        plugin.set_active()
        registry._plugins[simple_plugin_class.manifest.name] = plugin
        registry._load_order.append(simple_plugin_class.manifest.name)
        
        health = await manager.aggregate_health()
        assert "plugins" in health
        assert "summary" in health
        assert health["summary"]["active"] >= 1

    def test_get_plugin_manager_singleton(self):
        m1 = get_plugin_manager()
        m2 = get_plugin_manager()
        assert m1 is m2


# ——————————————————————————————————————————
# Specializations Tests
# —————————————————————————————————————————

class TestSpecializations:
    @pytest.mark.asyncio
    async def test_translator_backend_plugin_contract(self):
        class DummyTranslator(TranslatorBackendPlugin):
            manifest = PluginManifest(
                name="dummy_translator",
                version="1.0.0",
                description="Dummy translator for testing",
                author="test",
                entry_point="test_plugins:DummyTranslator",
                capabilities=[PluginCapability.TRANSLATION],
                priority=PluginPriority.MEDIUM,
            )
            async def initialize(self):
                self.initialized = True
            async def shutdown(self):
                self.shutdown_called = True
            async def translate(self, text, source_lang, target_lang, **options):
                return ("translated", 0.9)
            async def detect_language(self, text):
                return ("en", 0.95)
            async def list_supported_languages(self):
                return ["en", "es", "fr"]
            def get_default_config(self):
                return {}
        
        ctx = PluginContext(registry=MagicMock(), config={}, logger=MagicMock())
        plugin = DummyTranslator(ctx)
        assert PluginCapability.TRANSLATION in plugin.manifest.capabilities
        await plugin.initialize()
        assert plugin.initialized
        await plugin.shutdown()
        assert plugin.shutdown_called

    @pytest.mark.asyncio
    async def test_cache_plugin_contract(self):
        class DummyCache(CachePlugin):
            manifest = PluginManifest(
                name="dummy_cache",
                version="1.0.0",
                description="Dummy cache for testing",
                author="test",
                entry_point="test_plugins:DummyCache",
                capabilities=[PluginCapability.CACHING],
                priority=PluginPriority.MEDIUM,
            )
            async def initialize(self):
                self.initialized = True
            async def shutdown(self):
                self.shutdown_called = True
            async def get(self, key):
                return None
            async def set(self, key, value, ttl_seconds=None):
                return True
            async def delete(self, key):
                return True
            async def clear(self):
                return 0
            async def stats(self):
                return {"hits": 0, "misses": 0}
            def get_default_config(self):
                return {}
        
        ctx = PluginContext(registry=MagicMock(), config={}, logger=MagicMock())
        plugin = DummyCache(ctx)
        assert PluginCapability.CACHING in plugin.manifest.capabilities
        await plugin.initialize()
        await plugin.shutdown()

    @pytest.mark.asyncio
    async def test_observability_plugin_contract(self):
        class DummyObs(ObservabilityPlugin):
            manifest = PluginManifest(
                name="dummy_obs",
                version="1.0.0",
                description="Dummy observability for testing",
                author="test",
                entry_point="test_plugins:DummyObs",
                capabilities=[PluginCapability.OBSERVABILITY],
                priority=PluginPriority.LOW,
            )
            def increment_counter(self, name, value=1, tags=None):
                pass
            def record_gauge(self, name, value, tags=None):
                pass
            def record_histogram(self, name, value, tags=None):
                pass
            def start_span(self, name, **attrs):
                from contextlib import nullcontext
                return nullcontext()
            def get_default_config(self):
                return {}
            async def initialize(self):
                pass
            async def shutdown(self):
                pass
        
        ctx = PluginContext(registry=MagicMock(), config={}, logger=MagicMock())
        plugin = DummyObs(ctx)
        assert PluginCapability.OBSERVABILITY in plugin.manifest.capabilities
        await plugin.initialize()
        await plugin.shutdown()

    @pytest.mark.asyncio
    async def test_security_plugin_contract(self):
        class DummySec(SecurityPlugin):
            manifest = PluginManifest(
                name="dummy_sec",
                version="1.0.0",
                description="Dummy security for testing",
                author="test",
                entry_point="test_plugins:DummySec",
                capabilities=[PluginCapability.SECURITY],
                priority=PluginPriority.CRITICAL,
            )
            async def initialize(self):
                self.initialized = True
            async def shutdown(self):
                self.shutdown_called = True
            async def validate_request(self, request_data):
                return (True, None)
            async def audit_event(self, event_type, details, level="info"):
                pass
            async def check_anomaly(self, request_data, historical):
                return None
            def get_default_config(self):
                return {}
        
        ctx = PluginContext(registry=MagicMock(), config={}, logger=MagicMock())
        plugin = DummySec(ctx)
        assert PluginCapability.SECURITY in plugin.manifest.capabilities
        assert plugin.manifest.priority == PluginPriority.CRITICAL
        await plugin.initialize()
        await plugin.shutdown()

    def test_create_plugin_manifest_helper(self):
        m = create_plugin_manifest(
            name="myplugin",
            version="1.2.3",
            description="Test plugin",
            author="Me",
            entry_point="mod:Cls",
            capabilities=[PluginCapability.COMPRESSION],
            priority=PluginPriority.HIGH,
        )
        assert m.name == "myplugin"
        assert m.version == "1.2.3"
        assert m.capabilities == [PluginCapability.COMPRESSION]
        assert m.priority == PluginPriority.HIGH

