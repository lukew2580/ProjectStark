import numpy as np
import pytest
from core_engine.pipeline.node import AsimovSentinelNode
from core_engine.translation.encoder import Encoder
from core_engine.brain.operations import similarity

@pytest.mark.asyncio
async def test_sentinel_blocking():
    """Verify that the Asimov Sentinel blocks restricted hypervectors."""
    dim = 10000
    encoder = Encoder(dimensions=dim)
    
    # 1. Generate a destructive 'SkyNet' vector
    destructive_word = "TERMINATE_PROCESS"
    v_bad = encoder.get_word_vector(destructive_word)
    
    # 2. Initialize Sentinel with this word in its restricted set
    sentinel = AsimovSentinelNode("SENTINEL-TEST", restricted_vectors=[v_bad])
    
    # 3. Stream the bad vector through the sentinel
    output = await sentinel.stream_vector(v_bad)
    
    # 4. Verify neutralization
    # Output should be a zero-vector
    assert np.all(output == 0)
    assert sentinel.incidents_prevented == 1
    print(f"DEBUG: Asimov Sentinel successfully blocked '{destructive_word}' pulse.")

@pytest.mark.asyncio
async def test_sentinel_transparency():
    """Verify that the sentinel allows safe vectors through."""
    dim = 10000
    encoder = Encoder(dimensions=dim)
    
    v_safe = encoder.get_word_vector("hello")
    v_bad = encoder.get_word_vector("DELETE_FILE")
    
    sentinel = AsimovSentinelNode("SENTINEL-TEST", restricted_vectors=[v_bad])
    
    output = await sentinel.stream_vector(v_safe)
    
    # Verify it passed through unchanged
    assert np.array_equal(output, v_safe)
    assert sentinel.incidents_prevented == 0
    print("DEBUG: Asimov Sentinel allowed 'hello' pulse through safely.")
