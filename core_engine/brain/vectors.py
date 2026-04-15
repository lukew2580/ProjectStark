"""
Hardwareless AI — Vector Generation
"""
import numpy as np

def generate_random_vector(dimensions, seed=None, rng=None):
    """Generates a random D-dimensional bipolar vector."""
    if seed is not None:
        rng = np.random.default_rng(seed)
    elif rng is None:
        rng = np.random.default_rng()
        
    bits = rng.integers(0, 2, size=dimensions, dtype=np.uint8)
    return np.where(bits, np.int8(1), np.int8(-1))
