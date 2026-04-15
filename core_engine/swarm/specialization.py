"""
Hardwareless AI — Fuzzy Semantic Specialization
Uses seed-based dimension masking for overlapping expert domains.
"""
import numpy as np
import hashlib

def get_domain_mask(domain_name, dimensions, density=0.25):
    """
    Generates a sparse binary mask for a specific semantic domain.
    Uses MD5 hash of domain_name as a seed for determinism.
    """
    # Deterministic seed from name
    seed_hash = hashlib.md5(domain_name.encode()).digest()
    seed = int.from_bytes(seed_hash[:4], "big")
    rng = np.random.default_rng(seed)
    
    # Generate sparse 0/1 mask
    mask = rng.choice([False, True], size=dimensions, p=[1-density, density])
    return mask

def create_fuzzy_mask(domains, dimensions, density=0.25):
    """
    Combines multiple domain masks into a single overlapping subspace.
    Handles 'Unresolved Variants' that span across semantic boundaries.
    """
    final_mask = np.zeros(dimensions, dtype=bool)
    for domain in domains:
        domain_mask = get_domain_mask(domain, dimensions, density)
        final_mask |= domain_mask
    return final_mask

def get_fuzzy_transformation(dimensions, domains, density=0.25):
    """
    Generates a transformation vector that is IDENTITY (+1) 
    outside of the semantic Expert subspaces.
    """
    # Start with all identity
    transformation = np.ones(dimensions, dtype=np.int8)
    
    # Generate the fuzzy mask (handles overlap naturally)
    mask = create_fuzzy_mask(domains, dimensions, density)
    
    # Generate random flips (-1) only within the expert subspace
    # We use a global random seed here for the ACTUAL 'intelligence' content
    rng = np.random.default_rng()
    flips = np.where(
        rng.integers(0, 2, size=int(mask.sum()), dtype=np.uint8),
        np.int8(1), np.int8(-1)
    )
    
    transformation[mask] = flips
    return transformation
