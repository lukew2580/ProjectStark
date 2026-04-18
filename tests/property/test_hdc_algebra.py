"""
Quality Infrastructure — Hypothesis Property Tests
Tests fundamental HDC algebra properties using generative strategies.
"""

import pytest

try:
    import hypothesis
    import hypothesis.strategies as st
    HYPOTHESIS_AVAILABLE = True
except ImportError:
    HYPOTHESIS_AVAILABLE = False
    pytest.skip("hypothesis not installed", allow_module_level=True)

# Import HDC system
from core_engine.brain import bind, bundle, permutation, similarity, normalize, generate_random_vector
from config.settings import DIMENSIONS

# Strategies
vectors = st.lists(
    st.floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False),
    min_size=DIMENSIONS,
    max_size=DIMENSIONS,
).map(lambda lst: np.array(lst, dtype=np.float32))

scalar_binary_floats = st.floats(min_value=-10.0, max_value=10.0, allow_nan=False, allow_infinity=False)

@given(v1=vectors, v2=vectors, scalar=scalar_binary_floats)
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=200)
def test_binding_self_inverse(v1, v2, scalar):
    """Binding should be approximately self-inverse: bind(X, Y, Y) ≈ X"""
    # bind(a, b) = a ⊗ b; bind(bind(a,b), b) = a ⊗ (b ⊗ b) ≈ a (b⊙b ≈ identity)
    bound_ab = bind(v1, v2)
    bound_abb = bind(bound_ab, v2)
    
    # b ⊗ b ≈ identity? Actually HDC binding: for binary vectors, b ⊗ b = 1 (identity-ish)
    # But with continuous vectors, approx orthogonality works differently
    # The property is: A ⊗ B ⊗ B ≈ A if B ⊗ B ≈ I
    # Test correlation between bound_abb and v1
    sim = np.dot(bound_abb, v1) / (np.linalg.norm(bound_abb) * np.linalg.norm(v1) + 1e-8)
    assert sim > 0.7  # High similarity expected


@given(v1=vectors, v2=vectors)
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=200)
def test_binding_commutative(v1, v2):
    """Binding is commutative: bind(A, B) ≈ bind(B, A)"""
    ab = bind(v1, v2)
    ba = bind(v2, v1)
    sim = similarity(ab, ba)
    assert sim > 0.99  # Nearly perfect commutativity


@given(v1=vectors, v2=vectors)
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=100)
def test_bundling_commutative(v1, v2):
    """Bundling (addition) is commutative."""
    sum1 = bundle(v1, v2)
    sum2 = bundle(v2, v1)
    diff = np.linalg.norm(sum1 - sum2)
    assert diff < 1e-5


@given(v1=vectors)
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=200)
def test_bundling_identity(v1):
    """Bundling with zero vector returns approximate original."""
    zero = np.zeros_like(v1)
    result = bundle(v1, zero)
    sim = similarity(v1, result)
    assert sim > 0.99


@given(vectors_list=st.lists(vectors, min_size=3, max_size=10))
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=100)
def test_involution_property(vectors_list):
    """Repeated binding of self yields identity approximation over three."""
    a, b, c = vectors_list[:3]
    # (A ⊗ B) ⊗ C ⊗ C ⊗ B ≈ A
    # ((A ⊗ B) ⊗ C) ⊗ (C ⊗ B) = A ⊗ B ⊗ C ⊗ C ⊗ B ≈ A
    ab = bind(a, b)
    abc = bind(ab, c)
    cb = bind(c, b)
    roundtrip = bind(abc, cb)
    sim = similarity(a, roundtrip)
    assert sim > 0.6  # Diminishes with more


@given(v=vectors)
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=200)
def test_permutation_order(v):
    """Permuting twice with same seed returns near original."""
    p1 = permutation(v, seed=42)
    p2 = permutation(p1, seed=42)
    sim = similarity(v, p2)
    assert sim > 0.9  # Permutation is (approximately) involutive for integer seeds


@given(v=vectors)
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=200)
def test_normalization_unit_norm(v):
    """Normalized vectors have unit norm."""
    nv = normalize(v)
    norm = np.linalg.norm(nv)
    assert abs(norm - 1.0) < 1e-5


@given(v1=vectors, v2=vectors)
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=200)
def test_similarity_symmetric(v1, v2):
    """Similarity is symmetric."""
    sim_ab = similarity(v1, v2)
    sim_ba = similarity(v2, v1)
    assert abs(sim_ab - sim_ba) < 1e-5


@given(v1=vectors, v2=vectors)
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=200, deadline=None)
def test_bundle_distributes_over_binding(v1, v2):
    """
    Bundle distributes over binding (approximate).
    Bundle(A, bind(B, C)) ≈ bind(bundle(A, B), bundle(A, C))
    """
    S = v1
    A = v2
    B = generate_random_vector(DIMENSIONS, seed=123)
    C = generate_random_vector(DIMENSIONS, seed=456)
    
    left = bundle(S, bind(B, C))
    right = bind(bundle(S, B), bundle(S, C))
    sim = similarity(left, right)
    assert sim > 0.5  # HDC fuzzy distributive property


# Run with: pytest test_hdc_properties.py -v
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
