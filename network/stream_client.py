"""
Hardwareless AI — Async Hypervector Client
"""
import asyncio
import logging
import struct
from network.protocol import pack_vector, MAGIC, VERSION, HEADER_FORMAT_V2, FLAG_HEARTBEAT

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("HVClient")

class HypervectorClient:
    """
    Asynchronous client for sending hypervectors over the network.
    Now includes automatic heartbeat signaling.
    """

    def __init__(self, host="127.0.0.1", port=8888, crypto=None, heartbeat_interval=5):
        self.host = host
        self.port = port
        self.crypto = crypto
        self.heartbeat_interval = heartbeat_interval
        
        self.reader = None
        self.writer = None
        self._heartbeat_task = None

    async def connect(self):
        """Opens the connection and starts the heartbeat task."""
        logger.info(f"Connecting to {self.host}:{self.port} (Secure: {self.crypto is not None})")
        self.reader, self.writer = await asyncio.open_connection(
            self.host, self.port
        )
        logger.info("Connected")
        
        # Start background heartbeat
        if self.heartbeat_interval > 0:
            self._heartbeat_task = asyncio.create_task(self._pulse_loop())

    async def _pulse_loop(self):
        """Periodically sends a tiny heartbeat packet."""
        try:
            while True:
                await asyncio.sleep(self.heartbeat_interval)
                if self.writer:
                    # Construct a raw heartbeat (Flag 0x02, 0 payload)
                    # Use a fixed NodeID of 0 for client heartbeats unless specified
                    nonce = b'\x00' * 24
                    heartbeat = struct.pack(HEADER_FORMAT_V2, MAGIC, VERSION, 0, 0, FLAG_HEARTBEAT, nonce, 0)
                    self.writer.write(heartbeat)
                    await self.writer.drain()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Heartbeat loop failed: {e}")

    async def send_vector(self, vector, node_id=0, seq_id=0):
        """Packs and sends a hypervector."""
        is_dead = not self.writer or self.writer.is_closing() or (self.reader and self.reader.at_eof())
        
        if is_dead:
            print("DEBUG: Client connection is dead/closing. Reconnecting...")
            await self.connect()
            
        try:
            packet = pack_vector(vector, node_id, seq_id, crypto=self.crypto)
            self.writer.write(packet)
            await self.writer.drain()
        except Exception as e:
            print(f"DEBUG: Transport failure during drain: {e}")
            self.writer = None
            if self._heartbeat_task:
                self._heartbeat_task.cancel()
            raise

    async def close(self):
        """Closes the connection and stops heartbeats."""
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
            self.writer = None
            logger.info("Connection closed")
