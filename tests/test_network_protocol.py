import numpy as np
from network.protocol import pack_vector, unpack_vector

def test_protocol_serialization():
    dim = 10000
    v1 = np.random.choice([-1, 1], size=dim).astype(np.int8)
    node_id = 42
    seq_id = 123
    
    packet = pack_vector(v1, node_id, seq_id)
    # Header (17) + Payload (10000)
    assert len(packet) == 17 + dim
    
    v2, n2, s2 = unpack_vector(packet)
    assert np.array_equal(v1, v2)
    assert n2 == node_id
    assert s2 == seq_id

def test_invalid_magic():
    data = b'BAD!somepayload'
    try:
        unpack_vector(data)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert str(e) == "Invalid magic number"

def test_incomplete_packet():
    v = np.zeros(10, dtype=np.int8)
    packet = pack_vector(v)
    incomplete = packet[:-1]
    assert unpack_vector(incomplete) is None
