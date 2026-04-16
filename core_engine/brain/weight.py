"""
Hardwareless AI — Weighted Hypervector System
Adds mass, temporal decay, and semantic density to HDC vectors
"""
import time
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from core_engine.brain.vectors import generate_random_vector
from core_engine.brain.operations import bind, bundle, similarity


@dataclass
class WeightedVector:
    """A hypervector with temporal and semantic weight."""
    vector: np.ndarray
    mass: float = 1.0           # Semantic density (1.0 = baseline)
    age: float = 0.0           # Time since creation (seconds)
    last_access: float = 0.0   # Last retrieval time
    access_count: int = 0      # Times accessed


class VectorMass:
    """
    Adds weight/mass to the hypervector system.
    
    Concepts:
    - Mass: How "important" a vector is (access count + explicit weight)
    - Decay: Old vectors lose influence over time (temporal weight)
    - Density: Bundled vectors accumulate mass
    """
    
    def __init__(self, dimensions: int, decay_rate: float = 0.01):
        self.dimensions = dimensions
        self.decay_rate = decay_rate  # How fast vectors lose weight
        
        self._store: Dict[str, WeightedVector] = {}
        self._clock = time.time()
        
    def _now(self) -> float:
        return time.time() - self._clock
    
    def memorize(
        self,
        concept: str,
        vector: Optional[np.ndarray] = None,
        mass: float = 1.0
    ) -> WeightedVector:
        """Store a concept with mass."""
        if vector is None:
            vector = generate_random_vector(self.dimensions)
            
        wv = WeightedVector(
            vector=vector,
            mass=mass if mass is not None else 1.0,
            age=0.0,
            last_access=self._now(),
            access_count=0
        )
        self._store[concept] = wv
        return wv
    
    def recall(self, concept: str, decay: bool = True) -> Optional[WeightedVector]:
        """Retrieve a weighted vector."""
        if concept not in self._store:
            return None
            
        wv = self._store[concept]
        
        if decay:
            wv.last_access = self._now()
            wv.access_count += 1
            self._decay_vector(wv)
            
        return wv
    
    def _decay_vector(self, wv: WeightedVector):
        """Apply temporal decay to a vector's influence."""
        age = self._now() - wv.age
        decay_factor = np.exp(-self.decay_rate * age)
        wv.mass *= decay_factor
        wv.age = self._now()
        
    def get_weighted_vector(self, concept: str) -> Optional[np.ndarray]:
        """Get the effective vector (mass-weighted)."""
        wv = self.recall(concept, decay=True)
        if wv is None:
            return None
        return (wv.vector * wv.mass).astype(np.int8)
    
    def bind_weighted(
        self,
        wv_a: WeightedVector,
        wv_b: WeightedVector
    ) -> np.ndarray:
        """Bind two weighted vectors (mass combines)."""
        bound = bind(wv_a.vector, wv_b.vector)
        combined_mass = (wv_a.mass + wv_b.mass) / 2
        return (bound * combined_mass).astype(np.int8)
    
    def bundle_weighted(
        self,
        weighted_vectors: List[WeightedVector]
    ) -> np.ndarray:
        """Bundle multiple weighted vectors."""
        if not weighted_vectors:
            return np.zeros(self.dimensions, dtype=np.int8)
            
        vectors = [wv.vector for wv in weighted_vectors]
        bundled = bundle(vectors, self.dimensions)
        
        avg_mass = sum(wv.mass for wv in weighted_vectors) / len(weighted_vectors)
        return (bundled * avg_mass).astype(np.int8)
    
    def get_mass(self, concept: str) -> float:
        """Get the mass/importance of a concept."""
        wv = self._store.get(concept)
        return wv.mass if wv else 0.0
    
    def top_concepts(self, n: int = 10) -> List[Tuple[str, float]]:
        """Get top N by mass."""
        masses = [(c, wv.mass) for c, wv in self._store.items()]
        masses.sort(key=lambda x: x[1], reverse=True)
        return masses[:n]


class SemanticDensity:
    """
    Layer that adds semantic depth to basic vectors.
    Creates hierarchical representations.
    """
    
    def __init__(self, dimensions: int):
        self.dimensions = dimensions
        self._hierarchy: Dict[str, List[str]] = {}  # parent -> [children]
        self._associations: Dict[str, np.ndarray] = {}  # concept -> associated vector
        
    def add_hierarchy(self, parent: str, *children: str):
        """Build semantic hierarchy: parent encompasses children."""
        if parent not in self._hierarchy:
            self._hierarchy[parent] = []
        self._hierarchy[parent].extend(children)
        
    def add_association(self, concept: str, *related: str, mass: float = 1.0):
        """Link concepts semantically."""
        related_vectors = []
        for rel in related:
            seed = abs(hash(rel)) % (2**31)
            vec = generate_random_vector(self.dimensions, seed=seed)
            related_vectors.append(vec)
            
        if related_vectors:
            assoc = bundle(related_vectors, self.dimensions)
            self._associations[concept] = (assoc * mass).astype(np.int8)
            
    def enrich(self, vector: np.ndarray, concept: str) -> np.ndarray:
        """Enrich a vector with its semantic associations."""
        if concept in self._associations:
            assoc = self._associations[concept]
            enriched = bundle([vector, assoc], self.dimensions)
            return enriched
        return vector
    
    def get_children(self, concept: str) -> List[str]:
        return self._hierarchy.get(concept, [])
    
    def get_parents(self, concept: str) -> List[str]:
        parents = []
        for parent, children in self._hierarchy.items():
            if concept in children:
                parents.append(parent)
        return parents


class AttentionBinding:
    """
    Simulates attention by focusing weight on specific vector regions.
    """
    
    def __init__(self, dimensions: int):
        self.dimensions = dimensions
        self._focus_weights = {}
        
    def focus(self, concept: str, strength: float = 1.0):
        """Mark a concept as 'attended' with given strength."""
        self._focus_weights[concept] = np.clip(strength, 0.1, 2.0)
        
    def apply_attention(
        self,
        vector: np.ndarray,
        concept: str
    ) -> np.ndarray:
        """Apply attention weighting to a vector."""
        strength = self._focus_weights.get(concept, 1.0)
        
        if strength == 1.0:
            return vector
            
        vector_int = vector.astype(np.float32)
        weighted = vector_int * strength
        threshold = np.median(np.abs(weighted))
        
        result = np.where(
            np.abs(weighted) > threshold,
            np.sign(weighted) * np.int8(1),
            np.int8(-1)
        )
        return result


_global_mass: Optional[VectorMass] = None
_global_density: Optional[SemanticDensity] = None
_global_attention: Optional[AttentionBinding] = None


def get_mass(dimensions: int = 10000) -> VectorMass:
    global _global_mass
    if _global_mass is None:
        _global_mass = VectorMass(dimensions)
    return _global_mass


def get_density(dimensions: int = 10000) -> SemanticDensity:
    global _global_density
    if _global_density is None:
        _global_density = SemanticDensity(dimensions)
    return _global_density


def get_attention(dimensions: int = 10000) -> AttentionBinding:
    global _global_attention
    if _global_attention is None:
        _global_attention = AttentionBinding(dimensions)
    return _global_attention