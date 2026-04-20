"""
Hardwareless AI — Inference Core Package
Model-agnostic inference layer for LLM backends.
"""
from .registry import InferenceRegistry, ModelType, ModelConfig, get_inference_registry
from .backends import QwenBackend, OllamaBackend, TransformersBackend, CTranslate2Backend
from .converter import ModelConverter

__all__ = [
    "InferenceRegistry",
    "ModelType",
    "ModelConfig",
    "get_inference_registry",
    "QwenBackend",
    "OllamaBackend",
    "TransformersBackend",
    "CTranslate2Backend",
    "ModelConverter",
]
