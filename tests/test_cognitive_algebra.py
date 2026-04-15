import numpy as np
from core_engine.brain.learning import bind, bundle, permute
from core_engine.brain.vectors import generate_random_vector

def test_binding_reversibility():
    """Verify that HDC binding is mathematically reversible."""
    dim = 10000
    A = generate_random_vector(dim)
    B = generate_random_vector(dim)
    
    # Bind A with B
    C = bind(A, B)
    
    # Unbind A from C (in bipolar XOR binding, binding again is unbinding)
    D = bind(C, A)
    
    # D should be exactly B
    assert np.array_equal(D, B)
    print("DEBUG: Binding reversibility verified (A XOR B XOR A == B)")

def test_bundling_stability():
    """Verify that bundling multiple vectors maintains semantic similarity to components."""
    dim = 10000
    v1 = generate_random_vector(dim)
    v2 = generate_random_vector(dim)
    v3 = generate_random_vector(dim)
    
    # Bundle them
    composite = bundle([v1, v2, v3])
    
    # Check cosine similarity (dot product for bipolar)
    def similarity(a, b):
        return np.dot(a.astype(float), b.astype(float)) / dim
        
    s1 = similarity(composite, v1)
    s2 = similarity(composite, v2)
    s3 = similarity(composite, v3)
    
    # Higher similarity than random noise (~0.0)
    assert s1 > 0.3
    assert s2 > 0.3
    assert s3 > 0.3
    print(f"DEBUG: Bundling stability verified (Avg Similarity: {(s1+s2+s3)/3:.2f})")

def test_permutation_order():
    """Verify that permutation (shifting) creates a unique, non-similar vector."""
    dim = 10000
    v = generate_random_vector(dim)
    v_prime = permute(v, shift=1)
    
    def similarity(a, b):
        return np.dot(a.astype(float), b.astype(float)) / dim
        
    s = similarity(v, v_prime)
    
    # Should be very low (near zero)
    assert abs(s) < 0.05
    assert not np.array_equal(v, v_prime)
    print(f"DEBUG: Permutation order verified (Similarity of shift: {s:.4f})")
