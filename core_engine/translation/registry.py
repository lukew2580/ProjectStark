"""
Hardwareless AI — Multi-Backend Translation Registry
"""
import os
import asyncio
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from enum import Enum

class BackendType(Enum):
    MTRANSERVER = "mtranserver"
    LIBRETRANSLATE = "libretranslate"
    OPUS_MT = "opus_mt"
    FALLBACK = "fallback"

@dataclass
class TranslationResult:
    text: str
    source_lang: str
    target_lang: str
    backend: str
    confidence: float = 1.0

@dataclass
class BackendConfig:
    enabled: bool = True
    priority: int = 0
    endpoint: Optional[str] = None
    model_path: Optional[str] = None
    timeout: float = 30.0

class TranslationRegistry:
    """
    Manages multiple local translation backends with fallback logic.
    """
    def __init__(self):
        self.backends: Dict[BackendType, Any] = {}
        self.configs: Dict[BackendType, BackendConfig] = {}
        self._init_configs()

    def _init_configs(self):
        self.configs[BackendType.MTRANSERVER] = BackendConfig(
            priority=1,
            endpoint=os.environ.get("MTRANSERVER_URL", "http://127.0.0.1:8080")
        )
        self.configs[BackendType.LIBRETRANSLATE] = BackendConfig(
            priority=2,
            endpoint=os.environ.get("LIBRETRANSLATE_URL", "http://127.0.0.1:5000")
        )
        self.configs[BackendType.OPUS_MT] = BackendConfig(
            priority=3,
            model_path=os.environ.get("OPUS_MT_PATH", "models/opus-mt")
        )

    def register_backend(self, backend_type: BackendType, backend):
        self.backends[backend_type] = backend

    async def translate(
        self,
        text: str,
        source_lang: str = "auto",
        target_lang: str = "en"
    ) -> TranslationResult:
        sorted_backends = sorted(
            self.configs.items(),
            key=lambda x: x[1].priority
        )

        last_error = None
        for backend_type, config in sorted_backends:
            if not config.enabled:
                continue
            if backend_type not in self.backends:
                continue

            try:
                backend = self.backends[backend_type]
                result = await backend.translate(text, source_lang, target_lang)
                return result
            except Exception as e:
                last_error = e
                continue

        raise RuntimeError(f"All backends failed. Last error: {last_error}")

    async def translate_batch(
        self,
        texts: List[str],
        source_lang: str = "auto",
        target_lang: str = "en"
    ) -> List[TranslationResult]:
        return await asyncio.gather(*[
            self.translate(text, source_lang, target_lang)
            for text in texts
        ])

    def get_status(self) -> Dict[str, Any]:
        status = {}
        for backend_type, config in self.configs.items():
            is_healthy = backend_type in self.backends
            status[backend_type.value] = {
                "enabled": config.enabled,
                "priority": config.priority,
                "healthy": is_healthy
            }
        return status

    def enable_backend(self, backend_type: BackendType, enabled: bool = True):
        if backend_type in self.configs:
            self.configs[backend_type].enabled = enabled

    def set_priority(self, backend_type: BackendType, priority: int):
        if backend_type in self.configs:
            self.configs[backend_type].priority = priority


_global_registry: Optional[TranslationRegistry] = None

def get_registry() -> TranslationRegistry:
    global _global_registry
    if _global_registry is None:
        _global_registry = TranslationRegistry()
    return _global_registry