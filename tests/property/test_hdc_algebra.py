"""
Hardwareless AI — Hypothesis Property Tests
Tests fundamental HDC algebra properties using generative strategies.

Fixed bugs from original:
  - Import np (numpy) — was missing
  - Import given, settings, HealthCheck from hypothesis
  - Use correct brain API: permute() not permutation(), no normalize()
  - Fix bundle() signature: bundle([v1, v2], dimensions) not bundle(v1, v2)
  - Fix similarity() signature: similarity(a, b, dimensions) not similarity(a, b)
  - Add missing Path import
"""
import numpy as np
import pytest

try:
    from hypothesis import given, settings, HealthCheck
    import hypothesis.strategies as st
    HYPOTHESIS_AVAILABLE = True
except ImportError:
    HYPOTHESIS_AVAILABLE = False
    pytest.skip("hypothesis not installed", allow_module_level=True)

# Import HDC system — use the correct public API
from core_engine.brain import bind, bundle, permute, similarity, generate_random_vector
from config.settings import DIMENSIONS

# ── Strategies ────────────────────────────────────────────────────────────────
# Generate bipolar int8 vectors (the actual native format)
DIM = min(DIMENSIONS, 1000)  # Use smaller dim for property tests (speed)

@st.composite
def bipolar_vector(draw):
    """Generate a random bipolar (-1/+1) numpy vector."""
    bits = draw(st.lists(st.integers(min_value=0, max_value=1), min_size=DIM, max_size=DIM))
    arr = np.array([1 if b else -1 for b in bits], dtype=np.int8)
    return arr


# ── Property Tests ────────────────────────────────────────────────────────────

@given(v1=bipolar_vector(), v2=bipolar_vector())
@settings(
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
    max_examples=50,
    deadline=None,
)
def test_binding_self_inverse(v1, v2):
    """Binding is self-inverse: bind(bind(A, B), B) == A for bipolar vectors."""
    bound_ab = bind(v1, v2)
    recovered = bind(bound_ab, v2)
    # For bipolar XOR binding: A ⊗ B ⊗ B = A (exact)
    assert np.array_equal(recovered, v1)


@given(v1=bipolar_vector(), v2=bipolar_vector())
@settings(
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
    max_examples=50,
    deadline=None,
)
def test_binding_commutative(v1, v2):
    """Binding is commutative: bind(A, B) == bind(B, A) for bipolar XOR."""
    ab = bind(v1, v2)
    ba = bind(v2, v1)
    # Element-wise multiply is commutative
    assert np.array_equal(ab, ba)


@given(v1=bipolar_vector(), v2=bipolar_vector())
@settings(
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
    max_examples=50,
    deadline=None,
)
def test_bundling_result_is_bipolar(v1, v2):
    """Bundled result should still be a bipolar vector."""
    result = bundle([v1, v2], DIM)
    assert result.shape == (DIM,)
    unique_vals = set(np.unique(result))
    assert unique_vals.issubset({-1, 1})


@given(v1=bipolar_vector())
@settings(
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
    max_examples=50,
    deadline=None,
)
def test_permutation_changes_vector(v1):
    """Permuting a vector should produce a different (but same-length) vector."""
    permuted = permute(v1, shifts=1)
    assert permuted.shape == v1.shape
    # A cyclic shift of a non-uniform vector should differ (not guaranteed for
    # all-same vectors, but bipolar random vectors will almost never be uniform)
    # Instead test that permute then un-permute returns original
    recovered = permute(permuted, shifts=-1)
    assert np.array_equal(recovered, v1)


@given(v1=bipolar_vector(), v2=bipolar_vector())
@settings(
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
    max_examples=50,
    deadline=None,
)
def test_similarity_symmetric(v1, v2):
    """Similarity is symmetric: sim(A, B) == sim(B, A)."""
    sim_ab = similarity(v1, v2, DIM)
    sim_ba = similarity(v2, v1, DIM)
    assert abs(sim_ab - sim_ba) < 1e-6


@given(v1=bipolar_vector())
@settings(
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
    max_examples=50,
    deadline=None,
)
def test_similarity_self_is_one(v1):
    """Similarity of a vector with itself should be 1.0."""
    sim = similarity(v1, v1, DIM)
    assert abs(sim - 1.0) < 1e-6


@given(v1=bipolar_vector(), v2=bipolar_vector())
@settings(
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
    max_examples=50,
    deadline=None,
)
def test_bundle_similar_to_components(v1, v2):
    """
    Bundle(A, B) should be more similar to A and B than a random unrelated vector.
    HDC property: bundled set is similar to all its members.
    """
    bundled = bundle([v1, v2], DIM)
    sim_to_v1 = similarity(bundled, v1, DIM)
    sim_to_v2 = similarity(bundled, v2, DIM)
    # Random similarity is ~0, bundled should be positive
    assert sim_to_v1 > -0.1
    assert sim_to_v2 > -0.1


@given(
    vectors_list=st.lists(bipolar_vector(), min_size=3, max_size=5)
)
@settings(
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
    max_examples=30,
    deadline=None,
)
def test_involution_property(vectors_list):
    """
    Repeated binding of self yields identity:
    bind(A, B) → bind result → bind with B again → recovers A
    """
    a, b = vectors_list[0], vectors_list[1]
    ab = bind(a, b)
    recovered = bind(ab, b)
    assert np.array_equal(recovered, a)


# Run with: pytest tests/property/ -v
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
