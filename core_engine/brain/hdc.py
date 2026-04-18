"""
Hardwareless AI — Unified HDC API

This module provides backward-compatible imports while routing
all operations through the pluggable backend system.

Import this instead of core_engine.brain.vectors/operations directly.
"""
import numpy as np
from typing import Optional, List

# Import backend system
from core_engine.brain.backend import get_backend, initialize_backends, register_backend, set_active_backend

# Initialize backends on first import (lazy)
_backend_initialized = False

def _ensure_initialized():
    global _backend_initialized
    if not _backend_initialized:
        initialize_backends()
        _backend_initialized = True


# ============================================================================
# PUBLIC API — Compatible with original core_engine.brain.* modules
# ============================================================================

def generate_random_vector(dimensions: int, seed: Optional[int] = None, **kwargs) -> np.ndarray:
    """
    Generate a random hypervector.
    
    Args:
        dimensions: Vector dimensionality
        seed: Optional random seed for reproducibility
        **kwargs: Backend-specific arguments
    
    Returns:
        np.ndarray: HDC vector (dtype depends on backend)
    """
    _ensure_initialized()
    backend = get_backend()
    return backend.generate(dimensions, seed=seed, **kwargs)


def bind(vec_a: np.ndarray, vec_b: np.ndarray) -> np.ndarray:
    """
    Bind two vectors (association operation).
    
    Creates a new vector that is dissimilar to both inputs,
    representing the association of two concepts.
    """
    _ensure_initialized()
    backend = get_backend()
    return backend.bind(vec_a, vec_b)


def bundle(vectors: List[np.ndarray], dimensions: int, **kwargs) -> np.ndarray:
    """
    Bundle multiple vectors into a set.
    
    Creates a vector that is similar to all inputs,
    representing the set/conjunction of concepts.
    """
    _ensure_initialized()
    if not vectors:
        return np.zeros(dimensions, dtype=np.int8)
    backend = get_backend()
    return backend.bundle(vectors, dimensions, **kwargs)


def permute(vec: np.ndarray, shifts: int = 1) -> np.ndarray:
    """
    Permute (circularly shift) a vector.
    
    Encodes position/order. Essential for differentiating
    "dog bites man" vs "man bites dog".
    """
    _ensure_initialized()
    backend = get_backend()
    return backend.permute(vec, shifts)


def similarity(vec_a: np.ndarray, vec_b: np.ndarray, dimensions: int) -> float:
    """
    Compute cosine similarity between two vectors.
    
    For bipolar vectors, this is normalized dot product.
    """
    _ensure_initialized()
    backend = get_backend()
    return backend.similarity(vec_a, vec_b, dimensions)


# ============================================================================
# BACKEND MANAGEMENT — For advanced users / system diagnostics
# ============================================================================

def get_current_backend() -> str:
    """Get the name of the currently active backend."""
    _ensure_initialized()
    from core_engine.brain.backend import _registry
    return _registry._active_name


def list_available_backends() -> List[dict]:
    """List all registered backends with capabilities."""
    _ensure_initialized()
    from core_engine.brain.backend import _registry
    return _registry.list_backends()


def switch_backend(name: str) -> None:
    """Switch to a different HDC backend at runtime."""
    set_active_backend(name)
    print(f"[HDC] Switched to backend: {name}")


# ============================================================================
# ENVIRONMENT-BASED CONFIGURATION
# ============================================================================

import os

# Check HDC_BACKEND env var at import time
_hdc_backend = os.getenv("HDC_BACKEND", "").lower()

if _hdc_backend:
    # Force specific backend via environment
    if _hdc_backend == "legacy":
        from core_engine.brain.backend import LegacyNumpyBackend
        register_backend("legacy", LegacyNumpyBackend())
        set_active_backend("legacy")
    elif _hdc_backend == "torchhd":
        try:
            from core_engine.brain.backend import TorchHDBackend
            device = "cuda" if os.getenv("HDC_USE_GPU", "1").lower() in ("1", "true", "yes") else "cpu"
            model = os.getenv("HDC_TORCHHD_MODEL", "MAP")
            register_backend("torchhd", TorchHDBackend(model=model, device=device))
            set_active_backend("torchhd")
        except ImportError as e:
            print(f"[HDC] torchhd not available, falling back to legacy: {e}")
            from core_engine.brain.backend import LegacyNumpyBackend
            register_backend("legacy", LegacyNumpyBackend())
            set_active_backend("legacy")
    elif _hdc_backend == "hbllm":
        # Future: HBLLM integration
        raise NotImplementedError("HBLLM backend not yet implemented")
    # else: will autodetect below

# Autodetect if no explicit backend set
if not _hdc_backend:
    initialize_backends()

_b = get_backend()
print(f"[HDC] Backend active: {_b.name} — {_b.description}")
