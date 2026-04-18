"""Swarm Healing Unit Tests"""
import numpy as np
from core_engine.multi_agent import create_default_swarm, SwarmHealing

def test_swarm_creation():
    """Test default swarm creation."""
    swarm = create_default_swarm()
    assert swarm.get_state()["agents"] > 0

def test_swarm_healing():
    """Test swarm healing system."""
    swarm = create_default_swarm()
    healing = SwarmHealing(swarm)
    health = healing.get_health()
    assert health["agents"] > 0