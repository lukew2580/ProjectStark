"""
Hardwareless AI — Item Memory
"""
import os
import numpy as np
from typing import Dict, List, Optional, Tuple
from core_engine.brain.vectors import generate_random_vector


class Memory:
    def __init__(self, dimensions: int, rng: Optional[np.random.Generator] = None, persistence_path: Optional[str] = None):
        self.dimensions = dimensions
        self.items: Dict[str, np.ndarray] = {}  # concept_name -> hypervector
        self.rng = rng
        self.persistence_path = persistence_path
        
        if self.persistence_path:
            self.load_from_disk()

    def memorize(self, concept_name: str, vector: Optional[np.ndarray] = None) -> np.ndarray:
        """Stores a concept in Item Memory and persists it."""
        if vector is None:
            vector = generate_random_vector(self.dimensions, rng=self.rng)
        self.items[concept_name] = vector
        
        if self.persistence_path:
            self.save_to_disk()
            
        return vector

    def save_to_disk(self, path: Optional[str] = None) -> bool:
        """Saves memory items to a binary file."""
        target = path or self.persistence_path
        if not target:
            return False
            
        # Pack names and vectors separately for NumPy efficiency
        names = list(self.items.keys())
        vectors = list(self.items.values())
        np.savez_compressed(target, names=names, vectors=vectors)
        return True

    def load_from_disk(self, path: Optional[str] = None) -> bool:
        """Loads memory items from a binary file."""
        target = path or self.persistence_path
        if not target or not os.path.exists(target):
            return False
            
        try:
            data = np.load(target)
            names = data['names']
            vectors = data['vectors']
            self.items = {name: vec for name, vec in zip(names, vectors)}
            return True
        except Exception as e:
            print(f"Error loading memory vault: {e}")
            return False

    def recall(self, query_vector: np.ndarray, top_n: int = 1) -> List[Tuple[str, float]]:
        """
        Finds the closest concept(s) in memory to the query vector.
        Uses vectorized similarity for speed — no Python loops.
        """
        if not self.items:
            return []

        names = list(self.items.keys())
        memory_matrix = np.stack(list(self.items.values())).astype(np.int32)
        query_int = query_vector.astype(np.int32)

        scores = memory_matrix @ query_int / self.dimensions

        if top_n >= len(names):
            top_indices = np.argsort(scores)[::-1]
        else:
            top_indices = np.argpartition(scores, -top_n)[-top_n:]
            top_indices = top_indices[np.argsort(scores[top_indices])[::-1]]

        return [(names[i], float(scores[i])) for i in top_indices]
