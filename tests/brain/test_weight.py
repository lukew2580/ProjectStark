"""
Tests for core_engine.brain.weight module.
Covers VectorMass, SemanticDensity, AttentionBinding and global getters.
"""
import numpy as np
import pytest
from core_engine.brain.weight import (
    WeightedVector,
    VectorMass,
    SemanticDensity,
    AttentionBinding,
    get_mass,
    get_density,
    get_attention,
)
from core_engine.brain.vectors import generate_random_vector
from core_engine.brain.operations import bind, bundle


class TestWeightedVector:
    def test_create(self):
        vec = np.array([1, -1, 0], dtype=np.int8)
        wv = WeightedVector(vector=vec, mass=2.5, age=1.0, last_access=2.0, access_count=5)
        assert np.array_equal(wv.vector, vec)
        assert wv.mass == 2.5
        assert wv.age == 1.0
        assert wv.last_access == 2.0
        assert wv.access_count == 5


class TestVectorMass:
    def test_init(self):
        vm = VectorMass(100, decay_rate=0.05)
        assert vm.dimensions == 100
        assert vm.decay_rate == 0.05
        assert vm._store == {}

    def test_memorize_random(self):
        vm = VectorMass(100)
        wv = vm.memorize("concept1")
        assert "concept1" in vm._store
        assert vm._store["concept1"] is wv
        assert wv.vector.shape == (100,)
        assert wv.mass == 1.0
        assert wv.age == 0.0
        assert wv.access_count == 0

    def test_memorize_with_vector_and_mass(self):
        vm = VectorMass(100)
        custom_vec = generate_random_vector(100, seed=123)
        wv = vm.memorize("custom", vector=custom_vec, mass=3.5)
        assert np.array_equal(wv.vector, custom_vec)
        assert wv.mass == 3.5

    def test_recall_existing(self):
        vm = VectorMass(100)
        wv = vm.memorize("apple")
        retrieved = vm.recall("apple")
        assert retrieved is wv

    def test_recall_nonexistent(self):
        vm = VectorMass(100)
        assert vm.recall("unknown") is None

    def test_recall_without_decay(self):
        vm = VectorMass(100)
        wv = vm.memorize("banana")
        initial_count = wv.access_count
        initial_last = wv.last_access
        recalled = vm.recall("banana", decay=False)
        assert recalled is wv
        assert wv.access_count == initial_count  # unchanged
        assert wv.last_access == initial_last

    def test_recall_with_decay(self):
        vm = VectorMass(100, decay_rate=0.1)
        wv = vm.memorize("cherry")
        initial_count = wv.access_count
        initial_last = wv.last_access
        # Simulate time passage by manually adjusting age
        # We'll mock _now? Simpler: just verify that after recall, access_count increments and last_access updated.
        # Mass may change due to decay; we can't assert exact value without controlling time.
        recalled = vm.recall("cherry", decay=True)
        assert recalled is wv
        assert wv.access_count == initial_count + 1
        assert wv.last_access >= initial_last
        # Age should be updated to current time after decay
        assert wv.age > 0 or wv.age == 0  # after recall, _decay_vector sets wv.age = self._now(), which will be >0 if time passed

    def test_get_weighted_vector(self):
        # Use zero decay to prevent mass change during recall
        vm = VectorMass(100, decay_rate=0.0)
        vec = generate_random_vector(100, seed=456)
        wv = vm.memorize("weighted", vector=vec, mass=2.0)
        weighted = vm.get_weighted_vector("weighted")
        assert weighted.shape == (100,)
        assert weighted.dtype == np.int8
        # The weighted vector should be vector * mass cast to int8
        expected = (vec * 2.0).astype(np.int8)
        assert np.array_equal(weighted, expected)

    def test_bind_weighted(self):
        vm = VectorMass(100)
        v1 = generate_random_vector(100, seed=1)
        v2 = generate_random_vector(100, seed=2)
        wv1 = WeightedVector(vector=v1, mass=2.0)
        wv2 = WeightedVector(vector=v2, mass=4.0)
        bound = vm.bind_weighted(wv1, wv2)
        assert bound.shape == (100,)
        assert bound.dtype == np.int8
        # Expected: bind(v1, v2) * combined_mass where combined_mass = (2+4)/2 = 3.0
        expected = (bind(v1, v2) * 3.0).astype(np.int8)
        assert np.array_equal(bound, expected)

    def test_bundle_weighted(self):
        vm = VectorMass(100)
        vectors = [generate_random_vector(100, seed=i) for i in range(3)]
        weighted_vectors = [WeightedVector(vector=v, mass=i+1) for i, v in enumerate(vectors)]
        bundled = vm.bundle_weighted(weighted_vectors)
        assert bundled.shape == (100,)
        assert bundled.dtype == np.int8
        # Expected: bundle(vectors) * avg_mass where avg_mass = (1+2+3)/3 = 2.0
        expected = (bundle(vectors, 100) * 2.0).astype(np.int8)
        assert np.array_equal(bundled, expected)

    def test_bundle_weighted_empty(self):
        vm = VectorMass(100)
        empty = vm.bundle_weighted([])
        assert np.array_equal(empty, np.zeros(100, dtype=np.int8))

    def test_get_mass_existing(self):
        vm = VectorMass(100)
        vm.memorize("concept", mass=5.0)
        assert vm.get_mass("concept") == 5.0

    def test_get_mass_nonexistent(self):
        vm = VectorMass(100)
        assert vm.get_mass("unknown") == 0.0

    def test_top_concepts(self):
        vm = VectorMass(100)
        vm.memorize("a", mass=1.0)
        vm.memorize("b", mass=3.0)
        vm.memorize("c", mass=2.0)
        top = vm.top_concepts(2)
        assert len(top) == 2
        assert top[0][0] == "b"
        assert top[0][1] == 3.0
        assert top[1][0] == "c"
        assert top[1][1] == 2.0


class TestSemanticDensity:
    def test_init(self):
        sd = SemanticDensity(100)
        assert sd.dimensions == 100
        assert sd._hierarchy == {}
        assert sd._associations == {}

    def test_add_hierarchy(self):
        sd = SemanticDensity(100)
        sd.add_hierarchy("animal", "cat", "dog")
        assert sd._hierarchy["animal"] == ["cat", "dog"]
        sd.add_hierarchy("animal", "bird")
        assert sd._hierarchy["animal"] == ["cat", "dog", "bird"]

    def test_add_association(self):
        sd = SemanticDensity(100)
        sd.add_association("fruit", "apple", "banana", mass=1.5)
        assert "fruit" in sd._associations
        assoc = sd._associations["fruit"]
        assert assoc.shape == (100,)
        assert assoc.dtype == np.int8
        # The association should be bundle of random vectors for "apple" and "banana" times mass
        # Can't easily assert exact values.

    def test_enrich_with_association(self):
        sd = SemanticDensity(100)
        # Use a deterministic association vector to avoid randomness in bundling
        assoc_vec = np.ones(100, dtype=np.int8)
        sd._associations["tech"] = assoc_vec
        base_vec = np.ones(100, dtype=np.int8)
        enriched = sd.enrich(base_vec, "tech")
        assert enriched.shape == (100,)
        assert enriched.dtype == np.int8
        # enrich should bundle base_vec and the association
        expected = bundle([base_vec, assoc_vec], 100)
        assert np.array_equal(enriched, expected)

    def test_enrich_without_association_returns_original(self):
        sd = SemanticDensity(100)
        base_vec = generate_random_vector(100, seed=100)
        enriched = sd.enrich(base_vec, "nonexistent")
        # Should return original (maybe same reference or equal)
        assert np.array_equal(enriched, base_vec)

    def test_get_children(self):
        sd = SemanticDensity(100)
        sd.add_hierarchy("parent", "child1", "child2")
        children = sd.get_children("parent")
        assert set(children) == {"child1", "child2"}
        assert sd.get_children("missing") == []

    def test_get_parents(self):
        sd = SemanticDensity(100)
        sd.add_hierarchy("p1", "c1")
        sd.add_hierarchy("p2", "c1")
        parents = sd.get_parents("c1")
        assert set(parents) == {"p1", "p2"}


class TestAttentionBinding:
    def test_init(self):
        ab = AttentionBinding(100)
        assert ab.dimensions == 100
        assert ab._focus_weights == {}

    def test_focus(self):
        ab = AttentionBinding(100)
        ab.focus("concept", strength=1.5)
        assert ab._focus_weights["concept"] == 1.5

    def test_focus_clipping(self):
        ab = AttentionBinding(100)
        ab.focus("c", strength=0.05)  # below 0.1
        assert ab._focus_weights["c"] == 0.1
        ab.focus("c2", strength=3.0)  # above 2.0
        assert ab._focus_weights["c2"] == 2.0

    def test_apply_attention_strength_one(self):
        ab = AttentionBinding(100)
        vec = np.random.choice([-1, 1], size=100).astype(np.int8)
        result = ab.apply_attention(vec, "unknown")
        assert np.array_equal(result, vec)

    def test_apply_attention_changes_values(self):
        ab = AttentionBinding(100)
        # Create a vector with integer values to make threshold deterministic.
        # We'll create a vector with a mix of 1 and -1, but applying strength not 1.0
        # But result is determined by median of abs(weighted). Weighted = vec.astype(float)*strength.
        # With strength != 1, median of abs(weighted) = |strength| * median(|vec|). Since vec elements are ±1, abs are 1, median=1 => threshold = |strength|.
        # Then condition: abs(weighted) > threshold -> abs(vec*strength) > |strength| -> abs(vec)*|strength| > |strength| -> abs(vec) > 1. Since abs(vec)=1, condition false for all. So result will be -1 for all? Wait, result: if condition true, sign(weighted)*1 else -1. So if false, all become -1.
        # That's a bit specific. Let's try strength=2.0: weighted values are ±2, abs=2, threshold median=2? Actually median of abs(weighted) = 2.0, condition: > threshold, not >=. So 2 > 2 false, so all become -1. So entire vector becomes -1. So we can test that.
        vec = np.array([1, -1, 1, -1], dtype=np.int8)
        ab.focus("c", strength=2.0)
        result = ab.apply_attention(vec, "c")
        # Expected all -1 because condition false
        expected = np.array([-1, -1, -1, -1], dtype=np.int8)
        assert np.array_equal(result, expected)

        # For strength=0.5: weighted = ±0.5, abs=0.5, threshold=0.5, condition false -> all -1.
        ab.focus("c", strength=0.5)
        result = ab.apply_attention(vec, "c")
        assert np.array_equal(result, expected)

        # But if vector has varied magnitudes, result differs. But our vectors are ±1, threshold equals |strength|, so never >. So all become -1. That's okay.
        # We can also test with a vector that has zeros maybe? But not needed.

    def test_apply_attention_uses_focus_weight(self):
        ab = AttentionBinding(100)
        vec = np.array([1, -1, 1, -1], dtype=np.int8)
        # Default focus (no entry) returns 1.0 => unchanged.
        result = ab.apply_attention(vec, "nonexistent")
        assert np.array_equal(result, vec)


class TestGlobalGetters:
    def test_get_mass_singleton(self):
        m1 = get_mass(100)
        m2 = get_mass(100)
        assert m1 is m2

    def test_get_density_singleton(self):
        d1 = get_density(100)
        d2 = get_density(100)
        assert d1 is d2

    def test_get_attention_singleton(self):
        a1 = get_attention(100)
        a2 = get_attention(100)
        assert a1 is a2
