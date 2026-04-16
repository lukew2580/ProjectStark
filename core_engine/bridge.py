"""
Hardwareless AI — Universal Bridge Connector
Unifies all platform bridges (Android, iOS, Web, Desktop) into one API
"""
import asyncio
import json
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum

from network.stream_server import HypervectorServer
from network.stream_client import HypervectorClient
from core_engine.brain.vectors import generate_random_vector
from core_engine.brain.operations import similarity
from config.settings import DIMENSIONS


class Platform(Enum):
    PYTHON = "python"
    KOTLIN = "kotlin"      # Android
    SWIFT = "swift"        # iOS
    JAVASCRIPT = "js"       # Web
    RUST = "rust"          # Desktop


@dataclass
class BridgeNode:
    """A connected node from any platform."""
    node_id: int
    platform: Platform
    runtime: str
    last_seen: float
    capabilities: List[str]


class UniversalBridge:
    """
    The Universal Bridge - connects all platforms via HDC hypervectors.
    
    This is what makes Hardwareless AI unique:
    - Native Android (Kotlin) ↔ Native iOS (Swift) ↔ Web (JS) ↔ Desktop (Python/Rust)
    - All communicate via hypervector packets
    - No API translation layer - true protocol-level bridge
    """
    
    def __init__(self, dimensions: int = DIMENSIONS):
        self.dimensions = dimensions
        self.nodes: Dict[int, BridgeNode] = {}
        self._server: Optional[HypervectorServer] = None
        self._callback: Optional[Callable] = None
        
    async def start_server(self, port: int = 8888):
        """Start the hypervector server to receive from all platforms."""
        self._server = HypervectorServer(port=port, callback=self._on_packet)
        await self._server.start()
        print(f"🌉 Universal Bridge listening on port {port}")
        
    def _on_packet(self, vector, node_id, seq_id):
        """Handle incoming packet from any platform."""
        if node_id not in self.nodes:
            platform = self._infer_platform(node_id)
            self.nodes[node_id] = BridgeNode(
                node_id=node_id,
                platform=platform,
                runtime=self._get_runtime(platform),
                last_seen=0,
                capabilities=[]
            )
        self.nodes[node_id].last_seen = asyncio.get_event_loop().time()
        
        if self._callback:
            self._callback(vector, node_id, seq_id)
            
    def _infer_platform(self, node_id: int) -> Platform:
        """Infer platform from node ID range."""
        if 10000 <= node_id < 20000:
            return Platform.SWIFT
        elif 20000 <= node_id < 30000:
            return Platform.KOTLIN
        elif 30000 <= node_id < 40000:
            return Platform.JAVASCRIPT
        elif 40000 <= node_id < 50000:
            return Platform.RUST
        return Platform.PYTHON
    
    def _get_runtime(self, platform: Platform) -> str:
        runtimes = {
            Platform.PYTHON: "Python 3.10+",
            Platform.KOTLIN: "Kotlin/JVM",
            Platform.SWIFT: "Swift 5+",
            Platform.JAVASCRIPT: "Node.js/Browser",
            Platform.RUST: "Rust"
        }
        return runtimes.get(platform, "Unknown")
    
    async def connect_to(self, host: str, port: int) -> HypervectorClient:
        """Connect to another bridge node."""
        client = HypervectorClient(host, port)
        return client
    
    def register_callback(self, callback: Callable):
        """Register callback for incoming hypervectors."""
        self._callback = callback
        
    def get_connected_nodes(self) -> List[Dict[str, Any]]:
        """List all connected nodes across platforms."""
        return [
            {
                "node_id": node.node_id,
                "platform": node.platform.value,
                "runtime": node.runtime,
                "capabilities": node.capabilities
            }
            for node in self.nodes.values()
        ]
    
    def get_platform_stats(self) -> Dict[str, int]:
        """Get count of nodes per platform."""
        stats = {p.value: 0 for p in Platform}
        for node in self.nodes.values():
            stats[node.platform.value] += 1
        return stats
    
    async def broadcast_to_platform(
        self,
        vector: bytes,
        platform: Platform,
        client: HypervectorClient
    ):
        """Broadcast hypervector to all nodes of a specific platform."""
        # This would iterate through known nodes of that platform
        pass
    
    def create_hypervector_packet(
        self,
        vector_data: bytes,
        node_id: int = 0,
        seq_id: int = 0
    ) -> bytes:
        """Create a standardized hypervector packet (HV01 format)."""
        from network.protocol import pack_vector
        return pack_vector(vector_data, node_id, seq_id)


_global_bridge: Optional[UniversalBridge] = None


def get_bridge() -> UniversalBridge:
    global _global_bridge
    if _global_bridge is None:
        _global_bridge = UniversalBridge()
    return _global_bridge