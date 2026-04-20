"""
Hardwareless AI — Brain Package

HDC operations now use pluggable backends via the backend system.
Original API maintained for full backward compatibility.
"""
import numpy as np

# Core vector generation
from .vectors import generate_random_vector

# Core operations (HDC algebra) — uses backend system
# These are backend-aware, high-performance versions
from .operations import bind as op_bind, bundle as op_bundle, permute as op_permute, similarity

# Learning operations (higher-level, different semantics, memory-aware)
# These have distinct behavior and are NOT backend-aware yet
from .learning import (
    associate,
    bundle as learning_bundle,
    bind as learning_bind,
    permute as learning_permute
)

# Memory system
from .memory import Memory

# Weight/attention mechanisms
from .weight import VectorMass, SemanticDensity, AttentionBinding
from .weight import get_mass, get_density, get_attention

# Backend management
from .hdc import (
    get_backend,
    get_current_backend,
    list_available_backends,
    switch_backend,
    register_backend,
    permutation,
    normalize,
)

# ============================================================================
# EXPORT POLICY
# ============================================================================
# Default namespace uses operations module (backend-aware, high performance)
# This maintains compatibility with encoder/decoder/pipeline which expect
# bind/bundle/permute to be the fast, pure-HDC algebraic operations.
#
# Learning-specific versions are available as `learning_*` prefixed variants
# or by importing from core_engine.brain.learning directly.
#
# Historical note: Original code imported bind/bundle/permute from learning
# (which had slightly different semantics). We now expose fast versions by
# default and keep learning versions accessible under different names.

# Default exported symbols
bind = op_bind          # type: ignore[assignment]
bundle = op_bundle      # type: ignore[assignment]
permute = op_permute    # type: ignore[assignment]

# Exports
__all__ = [
    # HDC operations (backend-aware, fast)
    "generate_random_vector",
    "bind",
    "bundle",
    "permute",
    "permutation",  # alias for permute()
    "similarity",
    "normalize",    # unit-norm utility
    # Learning (higher-level, memory-aware, different semantics)
    "associate",
    # Explicitly named learning variants (for advanced use)
    "learning_bind",
    "learning_bundle",
    "learning_permute",
    # Memory
    "Memory",
    # Weight/attention
    "VectorMass",
    "SemanticDensity",
    "AttentionBinding",
    "get_mass",
    "get_density",
    "get_attention",
    # Backend management
    "get_backend",
    "get_current_backend",
    "list_available_backends",
    "switch_backend",
    "register_backend",
]

# Make learning variants available in namespace (not default but accessible)
learning_bind = learning_bind
learning_bundle = learning_bundle
learning_permute = learning_permute
