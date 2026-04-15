import asyncio
import numpy as np
import pytest
import nacl.secret
import nacl.utils
from network.crypto import SwarmCrypto
from network.stream_server import HypervectorServer
from network.stream_client import HypervectorClient

@pytest.mark.asyncio
async def test_secure_loopback():
    """
    Spins up a local server and client with encryption enabled,
    sends a vector, and verifies it arrives intact and authenticated.
    """
    dim = 10000
    host = "127.0.0.1"
    port = 8899
    
    # 1. Setup Crypto
    key = nacl.utils.random(nacl.secret.SecretBox.KEY_SIZE)
    crypto = SwarmCrypto(key)
    
    received_vectors = []
    
    async def handle_vector(vector, node_id, seq_id):
        received_vectors.append((vector, node_id, seq_id))
    
    # 2. Start Secure Server
    server = HypervectorServer(host=host, port=port, callback=handle_vector, crypto=crypto)
    server_task = asyncio.create_task(server.start())
    await asyncio.sleep(0.1)
    
    try:
        # 3. Start Secure Client
        client = HypervectorClient(host=host, port=port, crypto=crypto)
        await client.connect()
        
        # 4. Send Vector
        v_send = np.random.choice([-1, 1], size=dim).astype(np.int8)
        await client.send_vector(v_send, node_id=101, seq_id=1)
        
        # 5. Wait for it to arrive
        await asyncio.sleep(0.2)
        
        assert len(received_vectors) == 1
        v_recv, n_recv, _ = received_vectors[0]
        
        assert np.array_equal(v_send, v_recv)
        assert n_recv == 101
        
        await client.close()
    finally:
        await server.stop()
        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass

@pytest.mark.asyncio
async def test_authentication_failure():
    """
    Verifies that a server with the WRONG key correctly drops/rejects packets.
    """
    dim = 10000
    host = "127.0.0.1"
    port = 8898
    
    key_server = nacl.utils.random(nacl.secret.SecretBox.KEY_SIZE)
    key_client = nacl.utils.random(nacl.secret.SecretBox.KEY_SIZE)
    
    crypto_server = SwarmCrypto(key_server)
    crypto_client = SwarmCrypto(key_client)
    
    received_vectors = []
    async def handle_vector(vector, node_id, seq_id):
        received_vectors.append(vector)
    
    server = HypervectorServer(host=host, port=port, callback=handle_vector, crypto=crypto_server)
    server_task = asyncio.create_task(server.start())
    await asyncio.sleep(0.1)
    
    try:
        client = HypervectorClient(host=host, port=port, crypto=crypto_client)
        await client.connect()
        
        v_send = np.zeros(dim, dtype=np.int8)
        await client.send_vector(v_send)
        
        await asyncio.sleep(0.2)
        
        # Encryption should fail authentication on server side, so no vector received
        assert len(received_vectors) == 0
        
        await client.close()
    finally:
        await server.stop()
        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass
