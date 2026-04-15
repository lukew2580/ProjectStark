"""
HV01 Runtime Core
h1v3-runtime-2026.0.1.0
Reference Swarm Runtime Implementation
"""

import asyncio
import time
from typing import Dict, Set, Optional, Callable, Any
from collections import defaultdict

from .packet import Packet, Flags
from .vector import HyperVector


class HV01Runtime:
    def __init__(self, node_id: int):
        self.node_id = node_id
        self.sequence_counter = 0
        self.running = False

        # Runtime state
        self.vector_memory: Dict[int, HyperVector] = {}
        self.peer_nodes: Set[int] = set()
        self.message_handlers: Dict[Flags, Callable[[Packet], Any]] = {}
        self.subscriptions: Set[int] = set()

        # Statistics
        self.packets_sent = 0
        self.packets_received = 0
        self.start_time = 0.0

        # Register default handlers
        self._register_default_handlers()

    def _register_default_handlers(self):
        self.register_handler(Flags.HEARTBEAT, self._handle_heartbeat)
        self.register_handler(Flags.ACKNOWLEDGE, self._handle_acknowledge)

    def register_handler(self, flag: Flags, handler: Callable[[Packet], Any]):
        """Register a callback handler for specific packet types"""
        self.message_handlers[flag] = handler

    def generate_sequence_id(self) -> int:
        """Generate next sequential packet ID"""
        self.sequence_counter += 1
        return self.sequence_counter

    def send_vector(self, destination: int, vector: HyperVector, flags: Flags = Flags(0)) -> Packet:
        """Package and send a hypervector to a destination node"""
        packet = Packet.create(
            node_id=self.node_id,
            seq_id=self.generate_sequence_id(),
            payload=vector.to_bytes(),
            flags=flags
        )
        self.packets_sent += 1
        return packet

    def receive_packet(self, data: bytes) -> Optional[HyperVector]:
        """Process incoming packet data"""
        try:
            packet = Packet.unpack(data)
            self.packets_received += 1

            # Dispatch to registered handlers
            for flag, handler in self.message_handlers.items():
                if flag in packet.header.flags:
                    handler(packet)

            # Extract and return hypervector
            if len(packet.payload) == 10000:
                return HyperVector(packet.payload)

            return None

        except ValueError:
            return None

    def _handle_heartbeat(self, packet: Packet):
        """Handle incoming heartbeat packet"""
        self.peer_nodes.add(packet.header.node_id)

    def _handle_acknowledge(self, packet: Packet):
        """Handle acknowledge packet"""
        pass

    def start(self):
        """Start the runtime event loop"""
        self.running = True
        self.start_time = time.time()

    def stop(self):
        """Stop the runtime"""
        self.running = False

    def uptime(self) -> float:
        """Return runtime uptime in seconds"""
        return time.time() - self.start_time if self.start_time > 0 else 0.0

    def __repr__(self) -> str:
        return (f"HV01Runtime(node={self.node_id}, "
                f"sent={self.packets_sent}, "
                f"received={self.packets_received}, "
                f"peers={len(self.peer_nodes)})")