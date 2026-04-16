"""
Hardwareless AI — Translation Backends
"""
from .mtranserver import MTranServerBackend
from .libretranslate import LibreTranslateBackend
from .opus_mt import OpusMTBackend

__all__ = [
    "MTranServerBackend",
    "LibreTranslateBackend",
    "OpusMTBackend"
]