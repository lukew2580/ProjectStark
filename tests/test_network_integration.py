import asyncio
import numpy as np
import pytest
from network.stream_server import HypervectorServer
from network.stream_client import HypervectorClient

@pytest.mark.asyncio
async def test_network_loopback():
    """
    Spins up a local server and client, sends a vector, 
    and verifies it arrives intact.
    """
    dim = 10000
    host = "127.0.0.1"
    port = 9999
    
    received_vectors = []
    
    async def handle_vector(vector, node_id, seq_id):
        received_vectors.append((vector, node_id, seq_id))
    
    # 1. Start Server
    server = HypervectorServer(host=host, port=port, callback=handle_vector)
    # Run server in background
    server_task = asyncio.create_task(server.start())
    
    # Give server a moment to start
    await asyncio.sleep(0.1)
    
    try:
        # 2. Start Client
        client = HypervectorClient(host=host, port=port)
        await client.connect()
        
        # 3. Send Vector
        v_send = np.random.choice([-1, 1], size=dim).astype(np.int8)
        node_id_send = 77
        seq_id_send = 1
        
        await client.send_vector(v_send, node_id_send, seq_id_send)
        
        # 4. Wait for it to arrive
        await asyncio.sleep(0.1)
        
        assert len(received_vectors) == 1
        v_recv, n_recv, s_recv = received_vectors[0]
        
        assert np.array_equal(v_send, v_recv)
        assert n_recv == node_id_send
        assert s_recv == seq_id_send
        
        # 5. Cleanup
        await client.close()
    finally:
        await server.stop()
        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass
