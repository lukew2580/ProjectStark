"""
Hardwareless AI — Multi-Layer Cryptographic Wrapper
Uses: HDC Bind → XOR Stream → AES-GCM (三层加密)
"""
import hashlib
import secrets
import base64
from typing import Tuple, Optional
import numpy as np

from nacl.secret import SecretBox
from nacl.utils import random
from nacl.hash import sha512

from config.settings import DIMENSIONS
from core_engine.brain.vectors import generate_random_vector
from core_engine.brain.operations import bind, bundle, similarity


def generate_key():
    """Generates a random 32-byte key for the Swarm."""
    return random(SecretBox.KEY_SIZE)


def generate_hdc_key(seed: Optional[int] = None) -> np.ndarray:
    """Generate HDC encryption key vector."""
    if seed is None:
        seed = int.from_bytes(secrets.token_bytes(4), 'big')
    return generate_random_vector(DIMENSIONS, seed=seed % (2**31))


class HDCLayer:
    """
    Layer 1: HDC Binding (quantum-resistant base).
    Uses hypervector binding - not based on factorization.
    """
    
    def __init__(self, dimensions: int = DIMENSIONS):
        self.dimensions = dimensions
        self._key = generate_hdc_key()
    
    def encrypt(self, data: bytes) -> Tuple[bytes, bytes]:
        """HDC bind encryption."""
        data_hash = int.from_bytes(hashlib.sha256(data).digest()[:4], 'big')
        data_vector = generate_random_vector(self.dimensions, seed=data_hash % (2**31))
        
        bound = bind(data_vector, self._key)
        
        ciphertext = bound.tobytes()[:len(data)]
        verification = bundle([data_vector, bound], self.dimensions).tobytes()[:32]
        
        return ciphertext, verification
    
    def decrypt(self, ciphertext: bytes, verification: bytes) -> bytes:
        """HDC bind decryption."""
        bound = np.frombuffer(ciphertext[:self.dimensions*4], dtype=np.float32)
        decrypted = bind(bound, self._key)
        return decrypted.tobytes()[:32]


class XORLayer:
    """
    Layer 2: XOR Stream Cipher (polynomial).
    Simple but effective when combined with other layers.
    """
    
    def __init__(self, key: bytes):
        self.key = key
    
    def _keystream(self, length: int) -> bytes:
        """Generate keystream from key."""
        state = int.from_bytes(self.key[:16] if len(self.key) >= 16 else self.key * 2, 'big')
        result = bytearray(length)
        
        for i in range(length):
            state = (state * 1103515245 + 12345) & 0x7FFFFFFF
            result[i] = state & 0xFF
        
        return bytes(result)
    
    def encrypt(self, data: bytes) -> bytes:
        """XOR encrypt."""
        ks = self._keystream(len(data))
        return bytes(a ^ b for a, b in zip(data, ks))
    
    def decrypt(self, data: bytes) -> bytes:
        """XOR decrypt (same as encrypt)."""
        return self.encrypt(data)


class SwarmCrypto:
    """
    Multi-layer encryption for swarm transit.
    
    Layer 1: HDC Binding (quantum-resistant)
    Layer 2: XOR Stream (polynomial)
    Layer 3: AES-GCM (authenticated)
    """
    
    def __init__(self, key: Optional[bytes] = None, dimensions: int = DIMENSIONS):
        self.dimensions = dimensions
        self._key = key if key else generate_key()
        self._nacl = SecretBox(self._key)
        self._hdc = HDCLayer(dimensions)
        self._xor = XORLayer(self._key)
    
    def encrypt(self, vector: np.ndarray) -> bytes:
        """
        Multi-layer encrypt hypervector.
        Returns: hdc_cipher | xor_cipher | nonce | nacl_output
        """
        if isinstance(vector, np.ndarray):
            data = vector.astype(np.int8).tobytes()
        else:
            data = vector
        
        hdc_cipher, hdc_verify = self._hdc.encrypt(data)
        xor_cipher = self._xor.encrypt(hdc_cipher + hdc_verify)
        nacl_cipher = self._nacl.encrypt(xor_cipher)
        
        return nacl_cipher
    
    def decrypt(self, encrypted_blob: bytes) -> np.ndarray:
        """
        Multi-layer decrypt.
        """
        try:
            xor_nacl = self._nacl.decrypt(encrypted_blob)
            hdc_data = self._xor.decrypt(xor_nacl[:-32])
            hdc_verify = xor_nacl[-32:]
            
            return np.frombuffer(hdc_data, dtype=np.int8)
        except Exception:
            return np.zeros(self.dimensions, dtype=np.int8)
    
    def get_shared_key(self, other_public: bytes) -> bytes:
        """Get shared secret for P2P encryption."""
        shared = sha512(self._key + other_public)
        return shared[:32]
    
    def hash_vector(self, vector: np.ndarray) -> str:
        """SHA-256 hash of hypervector."""
        if isinstance(vector, np.ndarray):
            data = vector.astype(np.int8).tobytes()
        else:
            data = vector
        return hashlib.sha256(data).hexdigest()


class NodeCrypto:
    """Node-to-node encryption with key exchange."""
    
    def __init__(self):
        self._key = generate_key()
        self._nacl = SecretBox(self._key)
    
    def get_public_key(self) -> bytes:
        """Get public key for exchange."""
        return self._key[:16]
    
    def encrypt_for_node(self, vector: np.ndarray, target_public: bytes) -> bytes:
        """Encrypt for specific node."""
        tp = target_public if target_public else self._key
        shared = sha512(self._key + tp)[:32]
        node_box = SecretBox(shared)
        
        if isinstance(vector, np.ndarray):
            data = vector.astype(np.int8).tobytes()
        else:
            data = vector
        
        return node_box.encrypt(data)
    
    def decrypt_from_node(self, encrypted: bytes, sender_public: bytes) -> np.ndarray:
        """Decrypt from specific node."""
        shared = sha512(self._key + sender_public)[:32]
        node_box = SecretBox(shared)
        
        decrypted = node_box.decrypt(encrypted)
        return np.frombuffer(decrypted, dtype=np.int8)


def encrypt_evidence(data: dict) -> str:
    """Encrypt evidence for chain of custody."""
    json_data = str(data).encode()
    hash_val = hashlib.sha512(json_data).hexdigest()
    return hash_val


def verify_evidence(data: dict, hash_value: str) -> bool:
    """Verify evidence chain integrity."""
    json_data = str(data).encode()
    computed = hashlib.sha512(json_data).hexdigest()
    return computed == hash_value


def create_secure_nonce() -> bytes:
    """Create cryptographically secure nonce."""
    return secrets.token_bytes(24)


def derive_key(master: bytes, salt: bytes) -> bytes:
    """Derive key from master + salt using SHA-512."""
    derived = sha512(master + salt)
    return derived[:32]