"""
Hardwareless AI — Network Protocol (HV01 v3)
Enhanced binary wire format with multi-layer encryption.
"""
import struct
import asyncio
import secrets
from enum import Flag, auto
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timezone
import hashlib
import numpy as np


MAGIC_V3 = b'HV01'
PROTOCOL_VERSION = 3
HEADER_SIZE_V3 = 42

MAGIC = MAGIC_V3
VERSION = PROTOCOL_VERSION
HEADER_SIZE_V2 = HEADER_SIZE_V3
HEADER_FORMAT_V2 = '!4sBII B 24s I'

FLAG_ENCRYPTED = 0x01
FLAG_HEARTBEAT = 0x02
FLAG_COMPRESSED = 0x04
FLAG_BROADCAST = 0x08
FLAG_ACKNOWLEDGE = 0x10


def pack_vector(vector: np.ndarray, node_id: int = 0, seq_id: int = 0, crypto: Any = None) -> bytes:
    """Pack hypervector into v3 binary packet."""
    raw_payload = vector.astype(np.int8).tobytes()
    flags = 0
    nonce = b'\x00' * 24
    
    if crypto:
        encrypted_blob = crypto.encrypt(vector)
        nonce = encrypted_blob[:24]
        payload = encrypted_blob[24:]
        flags |= FLAG_ENCRYPTED
    else:
        payload = raw_payload
    
    length = len(payload)
    header = struct.pack('!4sBII B 24s I', MAGIC_V3, PROTOCOL_VERSION, node_id, seq_id, flags, nonce, length)
    return header + payload


def unpack_vector(data: bytes, crypto: Any = None) -> Optional[np.ndarray]:
    """Unpack binary packet to hypervector."""
    if len(data) < 4 or data[:4] != MAGIC_V3:
        return None
    if len(data) < 5:
        return None
    
    version = data[4]
    if version != PROTOCOL_VERSION:
        return None
    
    header = struct.unpack('!4sBII B 24s I', data[:HEADER_SIZE_V3])
    flags = header[4]
    length = header[6]
    
    if len(data) < HEADER_SIZE_V3 + length:
        return None
    
    payload = data[HEADER_SIZE_V3:]
    
    if crypto and (flags & FLAG_ENCRYPTED):
        nonce = data[13:37]
        crypto_payload = nonce + payload
        try:
            decrypted = crypto.decrypt(crypto_payload)
            return decrypted
        except Exception:
            return None
    
    return np.frombuffer(payload, dtype=np.int8)


def compute_checksum(data: bytes) -> int:
    """Compute packet checksum."""
    return hashlib.crc32(data) & 0xFFFFFFFF


def verify_packet(data: bytes) -> bool:
    """Verify packet integrity."""
    if len(data) < HEADER_SIZE_V3:
        return False
    if data[:4] != MAGIC_V3:
        return False
    if data[4] != PROTOCOL_VERSION:
        return False
    return True


@dataclass
class PacketInfo:
    """Packet metadata."""
    node_id: int
    seq_id: int
    flags: int
    nonce: bytes
    length: int
    
    @classmethod
    def from_data(cls, data: bytes) -> 'PacketInfo':
        header = struct.unpack('!4sBII B 24s I', data[:HEADER_SIZE_V3])
        return cls(
            node_id=header[2],
            seq_id=header[3],
            flags=header[5],
            nonce=header[6],
            length=header[7]
        )


class NodeRegistry:
    """Registry of known swarm nodes."""
    
    def __init__(self):
        self._nodes: Dict[int, Dict] = {}
        self._keys: Dict[int, bytes] = {}
    
    def register(self, node_id: int, public_key: bytes = None, metadata: Dict = None):
        """Register node."""
        self._nodes[node_id] = {
            "registered_at": datetime.now(timezone.utc).isoformat(),
            "public_key": public_key,
            "metadata": metadata or {},
            "status": "active"
        }
        if public_key:
            self._keys[node_id] = public_key
    
    def unregister(self, node_id: int):
        """Unregister node."""
        if node_id in self._nodes:
            self._nodes[node_id]["status"] = "inactive"
    
    def is_active(self, node_id: int) -> bool:
        """Check if node is active."""
        return self._nodes.get(node_id, {}).get("status") == "active"
    
    def get_node(self, node_id: int) -> Optional[Dict]:
        """Get node info."""
        return self._nodes.get(node_id)
    
    def list_active(self) -> List[int]:
        """List active nodes."""
        return [nid for nid, info in self._nodes.items() if info.get("status") == "active"]
    
    def get_stats(self) -> Dict:
        """Registry statistics."""
        active = self.list_active()
        return {
            "total_registered": len(self._nodes),
            "active": len(active),
            "inactive": len(self._nodes) - len(active)
        }


_global_registry: Optional[NodeRegistry] = None


def get_node_registry() -> NodeRegistry:
    global _global_registry
    if _global_registry is None:
        _global_registry = NodeRegistry()
    return _global_registry