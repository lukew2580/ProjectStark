import numpy as np
from network.protocol import pack_vector, unpack_vector, verify_packet

def test_network_protocol_pack():
    """Test pack/unpack."""
    dim = 100
    v = np.random.choice([-1, 1], size=dim).astype(np.int8)
    
    packet = pack_vector(v, node_id=1, seq_id=1)
    assert verify_packet(packet) is True
    
    unpacked = unpack_vector(packet)
    assert unpacked is not None
    assert len(unpacked) == dim

def test_protocol_node_registry():
    """Test node registry."""
    from network.protocol import get_node_registry
    
    registry = get_node_registry()
    registry.register(1, b"test_key", {"origin": "local"})
    
    assert registry.is_active(1) is True
    assert len(registry.list_active()) == 1