"""
Hardwareless AI — Cryptographic Wrapper
Uses PyNaCl (SecretBox) for authenticated encryption.
"""
from nacl.secret import SecretBox
from nacl.utils import random
import numpy as np

def generate_key():
    """Generates a random 32-byte key for the Swarm."""
    return random(SecretBox.KEY_SIZE)

class SwarmCrypto:
    """
    Handles encryption and decryption of hypervectors 
    for secure swarm transit.
    """
    def __init__(self, key):
        self.box = SecretBox(key)

    def encrypt(self, vector):
        """
        Encrypts a hypervector. 
        Returns (ciphertext, nonce).
        """
        # Convert to raw bytes if it's a numpy array
        if isinstance(vector, np.ndarray):
            data = vector.astype(np.int8).tobytes()
        else:
            data = vector
            
        encrypted = self.box.encrypt(data)
        # nacl.secret.SecretBox.encrypt returns (nonce + ciphertext)
        # We can extract them if needed, or just send the blob
        return encrypted

    def decrypt(self, encrypted_blob):
        """
        Decrypts an encrypted blob and returns the raw int8 vector.
        Raises nacl.exceptions.CryptoError if authentication fails.
        """
        decrypted = self.box.decrypt(encrypted_blob)
        return np.frombuffer(decrypted, dtype=np.int8)
