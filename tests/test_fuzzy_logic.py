import numpy as np
import pytest
from core_engine.swarm.specialization import get_domain_mask, create_fuzzy_mask

def test_domain_determinism():
    """Verify that a domain always produces the same mask for a given dimension."""
    m1 = get_domain_mask("LOGIC", 10000)
    m2 = get_domain_mask("LOGIC", 10000)
    assert np.array_equal(m1, m2)
    
    # Different names should be different masks
    m3 = get_domain_mask("CODE", 10000)
    assert not np.array_equal(m1, m3)

def test_mask_overlap():
    """Verify that domains can overlap semantically."""
    dim = 10000
    m_logic = get_domain_mask("LOGIC", dim)
    m_code = get_domain_mask("CODE", dim)
    
    # Calculate overlap
    overlap = np.logical_and(m_logic, m_code)
    overlap_count = int(overlap.sum())
    
    print(f"DEBUG: LOGIC size: {m_logic.sum()}, CODE size: {m_code.sum()}")
    print(f"DEBUG: Overlap: {overlap_count} dimensions")
    
    # Theoretical overlap for 25% density is 10000 * 0.25 * 0.25 = ~625
    assert overlap_count > 0
    assert overlap_count < 2500 # Should not be identical

def test_fuzzy_combination():
    """Verify that multiple domains combine into a broader expert subspace."""
    dim = 10000
    combo = create_fuzzy_mask(["LOGIC", "CODE"], dim)
    
    m_logic = get_domain_mask("LOGIC", dim)
    m_code = get_domain_mask("CODE", dim)
    
    # Logic and Code dimensions should ALL be True in the combo
    assert np.all(combo[m_logic])
    assert np.all(combo[m_code])
    
    # Total active should be less than sum (due to overlap)
    assert combo.sum() < (m_logic.sum() + m_code.sum())
