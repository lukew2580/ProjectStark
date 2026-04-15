"""
Hardwareless AI — Network Protocol (v1)
Binary wire format for hypervector transit.
"""
import struct
import numpy as np

# HV01 (HyperVector 01)
MAGIC = b'HV01'
VERSION = 2
# v1: !4sBII I (17 bytes)
# v2: !4sBII B 24s I (42 bytes)
HEADER_FORMAT_V2 = '!4sBII B 24s I' 
HEADER_SIZE_V2 = struct.calcsize(HEADER_FORMAT_V2)

FLAG_ENCRYPTED = 0x01
FLAG_HEARTBEAT = 0x02

def pack_vector(vector, node_id=0, seq_id=0, crypto=None):
    """
    Packs a numpy int8 hypervector into a v2 binary packet.
    If crypto is provided, the payload is encrypted.
    """
    raw_payload = vector.astype(np.int8).tobytes()
    flags = 0
    nonce = b'\x00' * 24 # Default empty nonce
    
    if crypto:
        # box.encrypt returns (nonce + ciphertext)
        encrypted_blob = crypto.encrypt(raw_payload)
        nonce = encrypted_blob[:24]
        payload = encrypted_blob[24:]
        flags |= FLAG_ENCRYPTED
    else:
        payload = raw_payload
        
    length = len(payload)
    header = struct.pack(HEADER_FORMAT_V2, MAGIC, VERSION, node_id, seq_id, flags, nonce, length)
    return header + payload

def unpack_vector(data, crypto=None):
    """
    Unpacks a binary packet. Decrypts if encrypted flag is set and crypto is provided.
    """
    if len(data) < 4:
        return None
    if data[:4] != MAGIC:
        raise ValueError("Invalid magic number")
    if len(data) < 5:
        return None
        
    version = data[4]
    if version == 2:
        if len(data) < HEADER_SIZE_V2:
            return None
        header_data = data[:HEADER_SIZE_V2]
        _, _, node_id, seq_id, flags, nonce, length = struct.unpack(HEADER_FORMAT_V2, header_data)
        payload_data = data[HEADER_SIZE_V2:HEADER_SIZE_V2+length]
        
        if len(payload_data) < length:
            return None
            
        if flags & FLAG_ENCRYPTED:
            if not crypto:
                raise ValueError("Encrypted packet received but no crypto provided")
            # Reconstruct the blob (nonce + ciphertext) for SecretBox
            vector = crypto.decrypt(nonce + payload_data)
        else:
            vector = np.frombuffer(payload_data, dtype=np.int8)
            
        return vector, node_id, seq_id
    else:
        raise ValueError(f"Unsupported protocol version: {version}")
