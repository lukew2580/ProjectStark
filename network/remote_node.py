"""
Hardwareless AI — Remote Network Node
Acts as a proxy for a DataFlowNode living on a different machine.
Now supports dynamic failover to secondary targets.
"""
import asyncio
import logging
from network.stream_client import HypervectorClient

logger = logging.getLogger("RemoteNode")

class RemoteNode:
    """
    A placeholder in the local pipeline that forwards 
    hypervectors to a remote HypervectorServer.
    Supports a list of targets for high-availability.
    """

    def __init__(self, node_id, targets=None):
        """
        targets: List of (host, port) tuples. e.g. [("10.0.0.1", 8888), ("10.0.0.2", 8888)]
        """
        if isinstance(node_id, str):
            self.node_id = hash(node_id) & 0xFFFFFFFF
        else:
            self.node_id = node_id
            
        self.targets = targets or [("127.0.0.1", 8888)]
        self.current_target_idx = 0
            
        import binascii
        from config.settings import SWARM_KEY
        from network.crypto import SwarmCrypto
        
        self._crypto = None
        if SWARM_KEY:
            self._crypto = SwarmCrypto(binascii.unhexlify(SWARM_KEY))
            
        self.client = None
        self.downstream = None

    def _is_client_active(self):
        """Checks if the current client is connected and active."""
        if not self.client or not self.client.writer:
            return False
        return not self.client.writer.is_closing()

    async def _get_client(self, force_reconnect=False):
        """Lazy-init or failover to a new client."""
        if not force_reconnect and self._is_client_active():
            return self.client
            
        if self.client:
            print(f"DEBUG: Closing stale client for target {self.current_target_idx}")
            await self.client.close()
            self.client = None
            
        # Try targets in order
        starting_idx = self.current_target_idx
        while True:
            host, port = self.targets[self.current_target_idx]
            try:
                print(f"DEBUG: Attempting connection to {host}:{port} (Index {self.current_target_idx})")
                self.client = HypervectorClient(host=host, port=port, crypto=self._crypto)
                await self.client.connect()
                print(f"DEBUG: Connected to {host}:{port}")
                return self.client
            except Exception as e:
                print(f"DEBUG: Connection to {host}:{port} failed: {e}")
                self.current_target_idx = (self.current_target_idx + 1) % len(self.targets)
                if self.current_target_idx == starting_idx:
                    print("DEBUG: ALL TARGETS EXHAUSTED")
                    raise ConnectionError("No reachable nodes in swarm targets list.")

    async def connect(self):
        await self._get_client()

    async def stream_vector(self, incoming):
        """
        Pipes the incoming vector to the remote machine with auto-failover.
        """
        client = await self._get_client()
        
        try:
            await client.send_vector(incoming, node_id=self.node_id)
        except Exception as e:
            print(f"DEBUG: Send failed on node {self.current_target_idx}: {type(e).__name__}: {e}")
            
            # Failover: Force reconnect to NEXT target
            self.current_target_idx = (self.current_target_idx + 1) % len(self.targets)
            print(f"DEBUG: Pivoting to target index {self.current_target_idx}")
            client = await self._get_client(force_reconnect=True)
            
            await client.send_vector(incoming, node_id=self.node_id)
            print("DEBUG: Swarm heal successful.")
            
        return None

    def get_metrics(self):
        host, port = self.targets[self.current_target_idx] if self.targets else ("None", 0)
        return {
            "node_id": f"{self.node_id} (Remote)",
            "status": "online" if self._is_client_active() else "isolated",
            "active_target": f"{host}:{port}",
            "redundancy": len(self.targets)
        }

    async def close(self):
        if self.client:
            await self.client.close()
