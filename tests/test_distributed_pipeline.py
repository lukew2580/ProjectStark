"""Distributed Pipeline Unit Tests"""
import numpy as np
from core_engine.pipeline.node import DataFlowNode

def test_node_creation():
    """Test DataFlowNode can be created."""
    node = DataFlowNode(node_id=1, dimensions=100)
    assert node.dimensions == 100

def test_node_metrics():
    """Test node has metrics."""
    node = DataFlowNode(node_id=1, dimensions=100)
    metrics = node.get_metrics()
    assert "ops" in metrics