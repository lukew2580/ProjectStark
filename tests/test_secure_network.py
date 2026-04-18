import numpy as np
import nacl.utils
from network.crypto import SwarmCrypto, generate_key, encrypt_evidence, verify_evidence

def test_crypto_key_generation():
    """Test key generation."""
    key = generate_key()
    assert len(key) == 32

def test_swarm_crypto_encrypt():
    """Test SwarmCrypto encrypt/decrypt."""
    key = generate_key()
    crypto = SwarmCrypto(key)
    
    vector = np.random.choice([-1, 1], size=1000).astype(np.int8)
    encrypted = crypto.encrypt(vector)
    
    assert len(encrypted) > 0
    assert encrypted != vector.tobytes()

def test_hash_vector():
    """Test vector hashing."""
    key = generate_key()
    crypto = SwarmCrypto(key)
    
    vector = np.random.choice([-1, 1], size=100).astype(np.int8)
    hash_val = crypto.hash_vector(vector)
    
    assert len(hash_val) == 64

def test_evidence_verification():
    """Test evidence encryption."""
    data = {"test": "evidence", "hash": "abc123"}
    hash_val = encrypt_evidence(data)
    
    assert verify_evidence(data, hash_val) is True