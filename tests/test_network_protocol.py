import numpy as np
from network.protocol import pack_vector, unpack_vector, verify_packet

def test_protocol_serialization():
    dim = 10000
    v1 = np.random.choice([-1, 1], size=dim).astype(np.int8)
    node_id = 42
    seq_id = 123
    
    packet = pack_vector(v1, node_id, seq_id)
    # Header (42 v3) + Payload (10000)
    assert len(packet) == 42 + dim, f"Expected {42+dim}, got {len(packet)}"
    
    v2 = unpack_vector(packet)
    assert v2 is not None
    assert np.array_equal(v1, v2)

def test_invalid_magic():
    data = b'BAD!somepayload'
    result = unpack_vector(data)
    # Should return None instead of raising
    assert result is None

def test_incomplete_packet():
    v = np.zeros(10, dtype=np.int8)
    packet = pack_vector(v)
    incomplete = packet[:-1]
    result = unpack_vector(incomplete)
    assert result is None

def test_verify_packet():
    v = np.zeros(10, dtype=np.int8)
    packet = pack_vector(v)
    assert verify_packet(packet) is True
    
    bad = b'BAD!'
    assert verify_packet(bad) is False