"""
Hardwareless AI — Core HDC Operations (Compatibility Layer)

This module maintains the original API while delegating to the
pluggable HDC backend system. DO NOT change import paths.
"""
import numpy as np
from typing import List

from core_engine.brain.hdc import get_backend

# Backend reference for performance-critical sections
_backend = None


def _get_backend():
    """Lazy-load the active backend."""
    global _backend
    if _backend is None:
        _backend = get_backend()
    return _backend


def bind(vec_a: np.ndarray, vec_b: np.ndarray) -> np.ndarray:
    """
    Binding (element-wise multiply).
    Creates a new vector that is dissimilar to both inputs,
    representing the *association* of two concepts.
    """
    return _get_backend().bind(vec_a, vec_b)


def bundle(vectors: List[np.ndarray], dimensions: int, **kwargs) -> np.ndarray:
    """
    Bundling (element-wise majority vote).
    Creates a vector that is *similar* to all inputs,
    representing the *set* of concepts.
    """
    return _get_backend().bundle(vectors, dimensions, **kwargs)


def permute(vec: np.ndarray, shifts: int = 1) -> np.ndarray:
    """
    Permutation (circular shift).
    Encodes POSITION / ORDER. permute(vec, 0) is position 0,
    permute(vec, 1) is position 1, etc.
    This is the critical operation that makes "dog bites man" ≠ "man bites dog".
    """
    return _get_backend().permute(vec, shifts)


def similarity(vec_a: np.ndarray, vec_b: np.ndarray, dimensions: int) -> float:
    """Cosine similarity for bipolar vectors → normalized dot product."""
    return _get_backend().similarity(vec_a, vec_b, dimensions)
