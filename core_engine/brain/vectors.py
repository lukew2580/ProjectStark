"""
Hardwareless AI — Vector Generation (Compatibility Layer)

This module maintains the original API while delegating to the
pluggable HDC backend system. DO NOT change import paths.
"""
from core_engine.brain.hdc import generate_random_vector

# Re-export for backward compatibility
__all__ = ["generate_random_vector"]
