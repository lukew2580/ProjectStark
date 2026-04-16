"""
Hardwareless AI — The GPU/CPU-less Hypervector Intelligence Platform
"""
__version__ = "0.3.0"

from core_engine.translation import (
    LanguageMatrix,
    BrainWeave,
    get_language_matrix,
    get_weave
)

from core_engine.brain import (
    get_mass,
    get_density,
    get_attention
)

__all__ = [
    "LanguageMatrix",
    "BrainWeave",
    "get_language_matrix",
    "get_weave",
    "get_mass",
    "get_density",
    "get_attention"
]