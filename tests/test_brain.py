import numpy as np
from core_engine.brain.vectors import generate_random_vector
from core_engine.brain.operations import bind, bundle, permute, similarity
from core_engine.brain.memory import Memory

def test_vector_generation():
    dim = 100
    vec = generate_random_vector(dim, seed=42)
    assert vec.shape == (dim,)
    assert set(np.unique(vec)).issubset({-1, 1})

def test_binding():
    dim = 100
    v1 = generate_random_vector(dim)
    v2 = generate_random_vector(dim)
    bound = bind(v1, v2)
    # Binding should be dissimilar to inputs
    assert similarity(bound, v1, dim) < 0.2
    assert similarity(bound, v2, dim) < 0.2
    # Binding is reversible
    assert np.array_equal(bind(bound, v1), v2)

def test_bundling():
    dim = 1000
    v1 = generate_random_vector(dim)
    v2 = generate_random_vector(dim)
    v3 = generate_random_vector(dim)
    bundled = bundle([v1, v2, v3], dim)
    # Bundling should be similar to all components
    assert similarity(bundled, v1, dim) > 0.1
    assert similarity(bundled, v2, dim) > 0.1
    assert similarity(bundled, v3, dim) > 0.1

def test_permutation():
    dim = 100
    v1 = generate_random_vector(dim)
    v2 = permute(v1, 1)
    v3 = permute(v1, 1)
    assert not np.array_equal(v1, v2)
    assert np.array_equal(v2, v3)
    # Permuting back
    assert np.array_equal(permute(v2, -1), v1)

def test_memory():
    dim = 100
    mem = Memory(dim)
    v_apple = mem.memorize("apple")
    v_banana = mem.memorize("banana")
    
    # Recall should find exact match
    results = mem.recall(v_apple, top_n=1)
    assert results[0][0] == "apple"
    assert results[0][1] > 0.99
