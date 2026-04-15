import asyncio
import numpy as np
import binascii
from network.stream_server import HypervectorServer
from network.remote_node import RemoteNode
from network.crypto import SwarmCrypto
from config.settings import SWARM_KEY

import network.protocol
import network.stream_server
import network.stream_client
import network.remote_node

print(f"DEBUG: Loading protocol from {network.protocol.__file__}")
print(f"DEBUG: Loading server from {network.stream_server.__file__}")
print(f"DEBUG: Loading client from {network.stream_client.__file__}")
print(f"DEBUG: Loading remote from {network.remote_node.__file__}")

async def main():
    dim = 10000
    host = "127.0.0.1"
    port_primary = 6901
    port_secondary = 6902
    
    # Setup Crypto
    crypto = None
    if SWARM_KEY:
        crypto = SwarmCrypto(binascii.unhexlify(SWARM_KEY))
        
    # Setup Servers
    results_p = []
    results_s = []
    async def cb_p(v, n, s): results_p.append(v)
    async def cb_s(v, n, s): results_s.append(v)
    
    server_p = HypervectorServer(host=host, port=port_primary, callback=cb_p, crypto=crypto)
    server_s = HypervectorServer(host=host, port=port_secondary, callback=cb_s, crypto=crypto)
    
    tp = asyncio.create_task(server_p.start())
    ts = asyncio.create_task(server_s.start())
    await asyncio.sleep(0.5)
    
    print("\n--- STEP 1: Connect to Swarm ---")
    remote = RemoteNode("Debug-Node", targets=[(host, port_primary), (host, port_secondary)])
    await remote.connect()
    
    print("\n--- STEP 2: Send v1 (Primary) ---")
    v1 = np.ones(dim, dtype=np.int8)
    await remote.stream_vector(v1)
    await asyncio.sleep(0.5)
    print(f"Primary Recv: {len(results_p)}, Secondary Recv: {len(results_s)}")
    
    print("\n--- STEP 3: Kill Primary ---")
    await server_p.stop()
    tp.cancel()
    await asyncio.sleep(1.0) # Wait for OS to clean up
    
    print("\n--- STEP 4: Send v2 (Should Failover) ---")
    v2 = np.full(dim, -1, dtype=np.int8)
    await remote.stream_vector(v2)
    await asyncio.sleep(1.0)
    print(f"Primary Recv: {len(results_p)}, Secondary Recv: {len(results_s)}")
    
    print("\n--- STEP 5: Integrity Verify ---")
    if len(results_s) > 0:
        match = np.array_equal(results_s[0], v2)
        print(f"Secondary Vector Match: {match}")
    else:
        print("CRITICAL: Secondary never received vector!")
        
    await remote.close()
    await server_s.stop()
    ts.cancel()

if __name__ == "__main__":
    asyncio.run(main())
