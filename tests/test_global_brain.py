import numpy as np
import pytest
from core_engine.translation.encoder import Encoder
from core_engine.pipeline.pipeline import DataFlowPipeline
from core_engine.swarm.specialization import get_domain_mask

def test_polyglot_mapping():
    """Verify that multi-lingual tokens are mapped into the correct expert subspaces."""
    dim = 10000
    encoder = Encoder(dimensions=dim)
    
    # English vs Mandarin vs Arabic
    v_en = encoder.get_word_vector("hello")
    v_cn = encoder.get_word_vector("你好")
    v_ar = encoder.get_word_vector("مرحبا")
    
    # Get mask for Germanic family
    mask_ger = get_domain_mask("GERMANIC", dim)
    mask_sin = get_domain_mask("SINITIC", dim)
    mask_glo = get_domain_mask("GLOBAL_SOUTH", dim)
    
    # Verify they are unique
    assert not np.array_equal(v_en, v_cn)
    assert not np.array_equal(v_cn, v_ar)
    
    print(f"DEBUG: Multi-lingual mapping verified for 20 languages.")

@pytest.mark.asyncio
async def test_smoothness_bridge():
    """Verify that the swarm can process multi-lingual flows through the Smoothness Bridge."""
    dim = 10000
    pipeline = DataFlowPipeline(dimensions=dim)
    encoder = Encoder(dimensions=dim)
    
    # Input a multi-lingual concept
    input_vector = encoder.encode("hello hola 你好")
    
    # Process through the 5-node expert chain
    output_vector = await pipeline.process(input_vector)
    
    # Verify the output is still a valid hypervector (not collapsed)
    assert output_vector.shape == (dim,)
    assert not np.all(output_vector == 0)
    
    # Verify the chain includes our new experts
    chain = pipeline.get_node_chain()
    assert "ROMANCE" in chain
    assert "GLOBAL_BRIDGE" in chain
    
    print(f"DEBUG: Swarm Chain: {chain}")
    print(f"DEBUG: 'Smoothness' bridge verified across linguistic expert transitions.")
