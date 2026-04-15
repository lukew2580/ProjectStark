import asyncio
import numpy as np
import pytest
from network.stream_server import HypervectorServer
from network.remote_node import RemoteNode

@pytest.mark.asyncio
async def test_swarm_healing_failover():
    """
    Integration test for self-healing:
    1. Start two remote servers (Primary and Secondary).
    2. Start a RemoteNode pointing to both.
    3. Send vectors.
    4. Kill Primary.
    5. Verify the stream continues on Secondary.
    """
    dim = 10000
    host = "127.0.0.1"
    port_primary = 6601
    port_secondary = 6602
    
    results_primary = []
    results_secondary = []
    
    # Check for global SWARM_KEY (security from Phase 4)
    import binascii
    from config.settings import SWARM_KEY
    from network.crypto import SwarmCrypto
    crypto = None
    if SWARM_KEY:
        crypto = SwarmCrypto(binascii.unhexlify(SWARM_KEY))
    
    async def cb_p(v, n, s): results_primary.append(v)
    async def cb_s(v, n, s): results_secondary.append(v)
    
    server_p = HypervectorServer(host=host, port=port_primary, callback=cb_p, crypto=crypto)
    server_s = HypervectorServer(host=host, port=port_secondary, callback=cb_s, crypto=crypto)
    
    task_p = asyncio.create_task(server_p.start())
    task_s = asyncio.create_task(server_s.start())
    await asyncio.sleep(0.1)
    
    try:
        # 1. Connect to both targets
        remote = RemoteNode("Healer-Node", targets=[(host, port_primary), (host, port_secondary)])
        await remote.connect()
        
        v1 = np.ones(dim, dtype=np.int8)
        await remote.stream_vector(v1)
        
        await asyncio.sleep(0.1)
        assert len(results_primary) == 1
        assert len(results_secondary) == 0
        
        # 2. KILL PRIMARY
        await server_p.stop()
        task_p.cancel()
        try:
            await task_p
        except asyncio.CancelledError:
            pass
        
        # Give the OS a moment to truly close the port
        await asyncio.sleep(0.5)
        
        # 3. Send again (must trigger failover because primary is GONE)
        v2 = np.full(dim, -1, dtype=np.int8)
        await remote.stream_vector(v2)
        
        await asyncio.sleep(0.2)
        assert len(results_primary) == 1
        assert len(results_secondary) == 1
        assert np.array_equal(results_secondary[0], v2)
        
        await remote.close()
    finally:
        await server_p.stop()
        await server_s.stop()
        task_p.cancel()
        task_s.cancel()
