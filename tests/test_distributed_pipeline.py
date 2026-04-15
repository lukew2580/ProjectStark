import asyncio
import numpy as np
import pytest
from core_engine.pipeline.node import DataFlowNode
from network.stream_server import HypervectorServer
from network.remote_node import RemoteNode

@pytest.mark.asyncio
async def test_distributed_forwarding():
    """
    Simulates a 2-node distributed pipeline:
    Gateway Node (Local) -> Remote Node (Socket) -> Execution Node (Remote Local)
    """
    dim = 10000
    host = "127.0.0.1"
    port = 7777
    
    # 1. Setup the 'Remote' environment (Server + Execution Node)
    execution_node = DataFlowNode("Remote-Execution-Node", dimensions=dim)
    received_results = []
    
    async def remote_callback(vector, node_id, seq_id):
        # The remote machine receives the vector and processes it locally
        res = await execution_node.stream_vector(vector)
        received_results.append(res)
    
    server = HypervectorServer(host=host, port=port, callback=remote_callback)
    server_task = asyncio.create_task(server.start())
    await asyncio.sleep(0.1)
    
    try:
        # 2. Setup the 'Local' environment (Gateway Node + Remote Proxy)
        gateway_node = DataFlowNode("Gateway-Node", dimensions=dim)
        remote_proxy = RemoteNode("Remote-Proxy", host=host, port=port)
        await remote_proxy.connect()
        
        gateway_node.connect(remote_proxy)
        
        # 3. Inject a vector
        test_vector = np.random.choice([-1, 1], size=dim).astype(np.int8)
        await gateway_node.stream_vector(test_vector)
        
        # 4. Wait for processing on the 'Remote' side
        await asyncio.sleep(0.2)
        
        assert len(received_results) == 1
        final_vector = received_results[0]
        
        # 5. Verify transformation
        # The final vector should be: test_vector * gateway_transform * execution_transform
        expected = (test_vector * gateway_node.transformation).astype(np.int8)
        expected = (expected * execution_node.transformation).astype(np.int8)
        
        assert np.array_equal(final_vector, expected)
        
        await remote_proxy.close()
    finally:
        await server.stop()
        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass
