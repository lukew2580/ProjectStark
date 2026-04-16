"""
Hardwareless AI — High-Dimensional Algebra Engine
"""
import numpy as np
from typing import List, Optional


def bundle(vectors: List[np.ndarray]) -> Optional[np.ndarray]:
    """
    Superposition of multiple hypervectors.
    Returns the element-wise sum followed by a threshold (sign).
    """
    if not vectors:
        return None
    sum_vector = np.sum(vectors, axis=0)
    # Thresholding back to bipolar (-1, 1)
    # 0 is randomly assigned to 1 or -1 to avoid bias
    bundled = np.where(sum_vector > 0, np.int8(1), np.int8(-1))
    
    # Randomly resolve zeros to maintain sparsity
    zeros = (sum_vector == 0)
    bundled[zeros] = np.random.choice([1, -1], size=int(zeros.sum())).astype(np.int8)
    
    return bundled


def bind(v1: np.ndarray, v2: np.ndarray) -> np.ndarray:
    """
    XOR-based binding in bipolar space.
    v1 * v2 is reversible: bind(bind(A, B), A) == B
    """
    return (v1 * v2).astype(np.int8)


def permute(vector: np.ndarray, shift: int = 1) -> np.ndarray:
    """
    Cyclic shift to represent sequence or structural order.
    """
    return np.roll(vector, shift)


def associate(memory, concept_name: str, related_concepts: List[str]):
    """
    Creates a bound representation of a concept and its relatives.
    e.g. associate(memory, "Greeting", ["Hello", "Hola", "Ciao"])
    """
    # Bundle the related concepts
    related_vectors = [memory.items[c] for c in related_concepts if c in memory.items]
    if not related_vectors:
        return None
    
    summary = bundle(related_vectors)
    
    # Bind with the parent concept
    parent_vector = memory.items.get(concept_name)
    if parent_vector is None:
        parent_vector = memory.memorize(concept_name)
        
    bound_identity = bind(parent_vector, summary)
    return bound_identity
