import numpy as np
import pytest
from core_engine.pipeline.node import DataFlowNode
from core_engine.pipeline.pipeline import DataFlowPipeline

@pytest.mark.asyncio
async def test_node_transformation():
    dim = 100
    # Create an identity node (+1 transformation)
    identity_transform = np.ones(dim, dtype=np.int8)
    node = DataFlowNode("test-node", dimensions=dim, transformation=identity_transform)
    
    vec = np.random.choice([-1, 1], size=dim).astype(np.int8)
    processed = await node.stream_vector(vec)
    assert np.array_equal(vec, processed)

@pytest.mark.asyncio
async def test_sparse_node():
    dim = 100
    # Create a node that flips ALL bits (-1 transformation)
    flip_transform = np.full(dim, -1, dtype=np.int8)
    node = DataFlowNode("sparse-node", dimensions=dim, transformation=flip_transform, sparse=True)
    
    vec = np.random.choice([-1, 1], size=dim).astype(np.int8)
    processed = await node.stream_vector(vec)
    assert np.array_equal(processed, -vec)
    assert node.get_metrics()["skip_ratio"] == "0.0%"  # All bits flipped, none skipped

@pytest.mark.asyncio
async def test_pipeline_chaining():
    dim = 100
    pipeline = DataFlowPipeline(node_count=3, dimensions=dim)
    assert len(pipeline.nodes) == 3
    assert pipeline.nodes[0].downstream == pipeline.nodes[1]
    assert pipeline.nodes[1].downstream == pipeline.nodes[2]
    
    vec = np.random.choice([-1, 1], size=dim).astype(np.int8)
    result = await pipeline.process(vec)
    assert result.shape == (dim,)
