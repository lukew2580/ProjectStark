"""
h1v3-runtime-2026.0.1.0
Reference implementation of the HV01 Hypervector Swarm Runtime v3

This is the official reference implementation that was previously only
available as private native bridges. Now released as open source for
the hardwareless-ai project.
"""

__version__ = "2026.0.1.0"
__protocol_version__ = 3

from .runtime import HV01Runtime
from .packet import Packet, Header, Flags
from .vector import HyperVector

__all__ = [
    "HV01Runtime",
    "Packet",
    "Header",
    "Flags",
    "HyperVector",
]