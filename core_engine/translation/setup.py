"""
Hardwareless AI — Translation Setup Helper
"""
import asyncio
from typing import Optional
from .registry import TranslationRegistry, get_registry, BackendType
from .backends import MTranServerBackend, LibreTranslateBackend, OpusMTBackend

def setup_translation_backends(
    mtranserver_url: Optional[str] = None,
    libretranslate_url: Optional[str] = None,
    opus_mt_path: Optional[str] = None,
    enable_mtranserver: bool = True,
    enable_libretranslate: bool = True,
    enable_opus_mt: bool = True
) -> TranslationRegistry:
    """
    Initialize all translation backends and register with global registry.
    
    Usage:
        from core_engine.translation import setup_translation_backends
        
        registry = setup_translation_backends(
            mtranserver_url="http://127.0.0.1:8080",
            enable_mtranserver=True,
            enable_libretranslate=True,
            enable_opus_mt=False  # Requires model download
        )
        
        # Translate
        result = await registry.translate("Hello", target_lang="es")
        print(result.text)  # "Hola"
    """
    registry = get_registry()
    
    if enable_mtranserver:
        endpoint = mtranserver_url or "http://127.0.0.1:8080"
        backend = MTranServerBackend(endpoint=endpoint)
        registry.register_backend(BackendType.MTRANSERVER, backend)
        print(f"✓ MTranServer backend registered: {endpoint}")
    
    if enable_libretranslate:
        endpoint = libretranslate_url or "http://127.0.0.1:5000"
        backend = LibreTranslateBackend(endpoint=endpoint)
        registry.register_backend(BackendType.LIBRETRANSLATE, backend)
        print(f"✓ LibreTranslate backend registered: {endpoint}")
    
    if enable_opus_mt:
        model_path = opus_mt_path or "models/opus-mt"
        backend = OpusMTBackend(model_path=model_path)
        registry.register_backend(BackendType.OPUS_MT, backend)
        print(f"✓ OPUS-MT backend registered: {model_path}")
    
    return registry

async def shutdown_backends():
    """Clean up all backend connections."""
    registry = get_registry()
    for backend_type, backend in registry.backends.items():
        if hasattr(backend, 'close'):
            await backend.close()
    print("✓ Translation backends shut down")

# Default usage example
if __name__ == "__main__":
    registry = setup_translation_backends()
    print(f"\nBackend status: {registry.get_status()}")