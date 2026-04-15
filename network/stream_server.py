"""
Hardwareless AI — Async Hypervector Server
"""
import asyncio
import logging
import struct
import time
from network.protocol import unpack_vector, HEADER_SIZE_V2, HEADER_FORMAT_V2, FLAG_HEARTBEAT

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("HVServer")

class HypervectorServer:
    """
    Asynchronous server that receives hypervector packets.
    Now includes 'Swarm Vitality' monitoring and aggressive shutdown support.
    """

    def __init__(self, host="0.0.0.0", port=8888, callback=None, crypto=None):
        self.host = host
        self.port = port
        self.callback = callback # Called as callback(vector, node_id, seq_id)
        self.crypto = crypto
        self._server = None
        
        # Swarm Registry (node_id -> last_seen_timestamp)
        self.active_nodes = {}
        # Active client connections for clean shutdown
        self._active_connections = set()

    async def _handle_client(self, reader, writer):
        addr = writer.get_extra_info('peername')
        logger.info(f"Connected to {addr}")
        self._active_connections.add(writer)
        
        buffer = b''
        try:
            while True:
                data = await reader.read(8192)
                if not data:
                    break
                
                buffer += data
                
                while len(buffer) >= HEADER_SIZE_V2:
                    try:
                        # Peek at header to check flags
                        _, _, node_id, seq_id, flags, _, length = struct.unpack(HEADER_FORMAT_V2, buffer[:HEADER_SIZE_V2])
                        
                        # Handle Vital Signals (Heartbeats)
                        if flags & FLAG_HEARTBEAT:
                            self.active_nodes[node_id] = time.time()
                            buffer = buffer[HEADER_SIZE_V2 + length:]
                            continue

                        # Handle Data Packets
                        result = unpack_vector(buffer, crypto=self.crypto)
                        if result is None:
                            break # Wait for more data
                            
                        vector, node_id, seq_id = result
                        packet_size = HEADER_SIZE_V2 + length
                        buffer = buffer[packet_size:]
                        
                        # Update activity
                        self.active_nodes[node_id] = time.time()
                        
                        if self.callback:
                            if asyncio.iscoroutinefunction(self.callback):
                                await self.callback(vector, node_id, seq_id)
                            else:
                                self.callback(vector, node_id, seq_id)
                                
                    except ValueError as e:
                        logger.error(f"Protocol/Crypto error from {addr}: {e}")
                        buffer = b'' 
                        break
                        
        except Exception as e:
            # We ignore 'Connection reset by peer' during aggressive shutdown
            if not writer.is_closing():
                logger.debug(f"Error handling client {addr}: {e}")
        finally:
            logger.debug(f"Closing connection to {addr}")
            self._active_connections.discard(writer)
            writer.close()
            try:
                await writer.wait_closed()
            except:
                pass

    def get_swarm_health(self):
        """Returns the status and architecture of all nodes in the swarm."""
        now = time.time()
        health = {}
        for node_id, seen in self.active_nodes.items():
            # Infer runtime architecture from ID ranges
            if 10000 <= node_id < 20000:
                runtime = "swift (native)"
            elif 20000 <= node_id < 30000:
                runtime = "kotlin (native)"
            else:
                runtime = "python"
                
            health[node_id] = {
                "last_seen": f"{now - seen:.2f}s ago",
                "status": "online" if (now - seen) < 30 else "offline",
                "runtime": runtime
            }
        return health

    async def start(self):
        self._server = await asyncio.start_server(
            self._handle_client, self.host, self.port
        )
        addr = self._server.sockets[0].getsockname()
        logger.info(f"Server listening on {addr}")
        async with self._server:
            await self._server.serve_forever()

    async def stop(self):
        """Aggressively stops the server and closes all active clients."""
        if self._server:
            logger.info(f"Stopping server on {self.port}...")
            self._server.close()
            
            # Aggressively close all active client writers
            for writer in list(self._active_connections):
                writer.close()
                
            await self._server.wait_closed()
            logger.info("Server stopped")
