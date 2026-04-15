"""
HV01 Hypervector Operations
2026.0.1.0 Standard
10,000 dimensional int8 hypervector implementation
"""

import numpy as np
from typing import List, Tuple

VECTOR_DIMENSIONS = 10000
VECTOR_DTYPE = np.int8


class HyperVector:
    def __init__(self, data=None):
        if data is None:
            self.data = np.zeros(VECTOR_DIMENSIONS, dtype=VECTOR_DTYPE)
        elif isinstance(data, np.ndarray):
            if data.shape != (VECTOR_DIMENSIONS,):
                raise ValueError(f"Hypervector must be {VECTOR_DIMENSIONS} dimensions")
            self.data = data.astype(VECTOR_DTYPE)
        elif isinstance(data, bytes):
            if len(data) != VECTOR_DIMENSIONS:
                raise ValueError(f"Hypervector bytes must be {VECTOR_DIMENSIONS} bytes")
            self.data = np.frombuffer(data, dtype=VECTOR_DTYPE)
        else:
            raise TypeError("Unsupported data type for HyperVector")

    @classmethod
    def random(cls) -> 'HyperVector':
        """Generate a random bipolar hypervector with ±1 values"""
        return cls(np.random.choice([-1, 1], size=VECTOR_DIMENSIONS).astype(VECTOR_DTYPE))

    @classmethod
    def zero(cls) -> 'HyperVector':
        """Generate an empty zero hypervector"""
        return cls(np.zeros(VECTOR_DIMENSIONS, dtype=VECTOR_DTYPE))

    def bind(self, other: 'HyperVector') -> 'HyperVector':
        """Binding operation: element-wise multiplication (circular convolution proxy)"""
        return HyperVector(self.data * other.data)

    def bundle(self, other: 'HyperVector') -> 'HyperVector':
        """Bundling operation: element-wise addition with clamping"""
        result = self.data + other.data
        np.clip(result, -127, 127, out=result)
        return HyperVector(result)

    def similarity(self, other: 'HyperVector') -> float:
        """Cosine similarity between two hypervectors"""
        dot = np.dot(self.data, other.data)
        norm_product = np.linalg.norm(self.data) * np.linalg.norm(other.data)
        return dot / norm_product if norm_product != 0 else 0.0

    def hamming(self, other: 'HyperVector') -> int:
        """Hamming distance between two hypervectors"""
        return int(np.sum(self.data != other.data))

    def permute(self, shift: int = 1) -> 'HyperVector':
        """Cyclic permutation of vector elements"""
        return HyperVector(np.roll(self.data, shift))

    def to_bytes(self) -> bytes:
        """Serialize to binary format"""
        return self.data.tobytes()

    def __add__(self, other: 'HyperVector') -> 'HyperVector':
        return self.bundle(other)

    def __mul__(self, other: 'HyperVector') -> 'HyperVector':
        return self.bind(other)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, HyperVector):
            return False
        return np.array_equal(self.data, other.data)

    def __repr__(self) -> str:
        return f"HyperVector(hash={hash(self.to_bytes())})"