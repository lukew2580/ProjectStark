"""
HV01 v3 Packet Protocol
2026.0.1.0 Specification
"""

import struct
import secrets
from enum import Flag, auto
from dataclasses import dataclass

MAGIC = 0x48563031  # 'HV01' Big Endian
PROTOCOL_VERSION = 3
HEADER_SIZE = 43  # magic(4) + version(1) + node_id(4) + seq_id(4) + flags(1) + nonce(24) + length(4)


class Flags(Flag):
    ENCRYPTED = auto()
    HEARTBEAT = auto()
    COMPRESSED = auto()
    ACKNOWLEDGE = auto()
    BROADCAST = auto()
    CRITICAL = auto()


@dataclass
class Header:
    node_id: int
    seq_id: int
    flags: Flags
    nonce: bytes
    length: int

    def pack(self) -> bytes:
        buffer = bytearray(HEADER_SIZE)
        struct.pack_into('>I', buffer, 0, MAGIC)
        struct.pack_into('B', buffer, 4, PROTOCOL_VERSION)
        struct.pack_into('>I', buffer, 5, self.node_id)
        struct.pack_into('>I', buffer, 9, self.seq_id)
        struct.pack_into('B', buffer, 13, self.flags.value)
        buffer[14:38] = self.nonce
        struct.pack_into('>I', buffer, 38, self.length)
        return bytes(buffer)

    @classmethod
    def unpack(cls, data: bytes) -> 'Header':
        if len(data) < HEADER_SIZE:
            raise ValueError("Invalid header size")

        magic = struct.unpack_from('>I', data, 0)[0]
        if magic != MAGIC:
            raise ValueError("Invalid packet magic number")

        version = struct.unpack_from('B', data, 4)[0]
        if version != PROTOCOL_VERSION:
            raise ValueError(f"Unsupported protocol version: {version}")

        return cls(
            node_id=struct.unpack_from('>I', data, 5)[0],
            seq_id=struct.unpack_from('>I', data, 9)[0],
            flags=Flags(struct.unpack_from('B', data, 13)[0]),
            nonce=data[14:38],
            length=struct.unpack_from('>I', data, 38)[0]
        )


@dataclass
class Packet:
    header: Header
    payload: bytes

    @classmethod
    def create(cls, node_id: int, seq_id: int, payload: bytes, flags: Flags = Flags(0)) -> 'Packet':
        nonce = secrets.token_bytes(24)
        header = Header(
            node_id=node_id,
            seq_id=seq_id,
            flags=flags,
            nonce=nonce,
            length=len(payload)
        )
        return cls(header=header, payload=payload)

    def pack(self) -> bytes:
        return self.header.pack() + self.payload

    @classmethod
    def unpack(cls, data: bytes) -> 'Packet':
        header = Header.unpack(data)
        payload = data[HEADER_SIZE:HEADER_SIZE + header.length]
        return cls(header=header, payload=payload)