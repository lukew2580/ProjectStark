"""
Hardwareless AI — Core HDC Operations
"""
import numpy as np
from typing import List, Optional
from core_engine.brain.vectors import generate_random_vector


def bind(vec_a: np.ndarray, vec_b: np.ndarray) -> np.ndarray:
    """
    Binding (element-wise multiply).
    Creates a new vector that is dissimilar to both inputs,
    representing the *association* of two concepts.
    """
    return (vec_a * vec_b).astype(np.int8)


def bundle(vectors: List[np.ndarray], dimensions: int, rng: Optional[np.random.Generator] = None) -> np.ndarray:
    """
    Bundling (element-wise majority vote).
    Creates a vector that is *similar* to all inputs,
    representing the *set* of concepts.
    """
    if not vectors:
        return np.zeros(dimensions, dtype=np.int8)
    stacked = np.stack(vectors)
    summed = stacked.sum(axis=0)
    # Break ties randomly for even-count bundles
    ties = (summed == 0)
    result = np.where(summed > 0, np.int8(1), np.int8(-1))
    if ties.any():
        tie_breaks = generate_random_vector(dimensions, rng=rng)
        result[ties] = tie_breaks[ties]
    return result


def permute(vec: np.ndarray, shifts: int = 1) -> np.ndarray:
    """
    Permutation (circular shift).
    Encodes POSITION / ORDER. permute(vec, 0) is position 0,
    permute(vec, 1) is position 1, etc.
    This is the critical operation that makes "dog bites man" ≠ "man bites dog".
    """
    return np.roll(vec, shifts).astype(np.int8)


def similarity(vec_a: np.ndarray, vec_b: np.ndarray, dimensions: int) -> float:
    """Cosine similarity for bipolar vectors → normalized dot product."""
    return float(np.dot(vec_a.astype(np.int32), vec_b.astype(np.int32))) / dimensions
