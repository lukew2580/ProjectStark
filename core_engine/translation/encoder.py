"""
Hardwareless AI — Text to Hypervector Encoder
"""
import numpy as np
import hashlib
from typing import Dict, List, Optional
from config.settings import DIMENSIONS
from core_engine.brain.vectors import generate_random_vector
from core_engine.brain.operations import permute, bundle


class Encoder:
    def __init__(self, dimensions: int = DIMENSIONS):
        self.dimensions = dimensions
        self._cache: Dict[str, np.ndarray] = {}

    def get_word_vector(self, word: str) -> np.ndarray:
        if word in self._cache:
            return self._cache[word]

        hash_bytes = hashlib.sha256(word.encode('utf-8')).digest()
        seed = int.from_bytes(hash_bytes[:4], 'big')
        vec = generate_random_vector(self.dimensions, seed=seed)

        self._cache[word] = vec
        return vec

    def bulk_ingest(self, concept_list: List[str]) -> int:
        """Pre-heats the cache with a list of semantic concepts (Repo DNA)."""
        count = 0
        for concept in concept_list:
            if concept and isinstance(concept, str):
                self.get_word_vector(concept)
                count += 1
        return count

    def encode(self, text: str) -> np.ndarray:
        words = text.lower().strip().split()
        if not words:
            return np.zeros(self.dimensions, dtype=np.int8)

        positional_vectors = []
        for position, word in enumerate(words):
            base_vec = self.get_word_vector(word)
            pos_vec = permute(base_vec, shifts=position)
            positional_vectors.append(pos_vec)

        return bundle(positional_vectors, self.dimensions)
