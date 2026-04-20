"""
Hardwareless AI — Inference Backend Registry
Manages multiple LLM backends with model selection.
"""
import os
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from enum import Enum


class ModelType(Enum):
    """Available model backends."""
    HARDWARELESS_CORE = "hardwareless-core"
    QWEN2_5_7B = "qwen2.5-7b"


@dataclass
class ModelConfig:
    """Configuration for a model backend."""
    model_type: ModelType
    name: str
    path: str
    device: str = "cpu"
    compute_type: str = "int8"
    enabled: bool = True
    priority: int = 0
    # New: which backend implementation to use
    backend_impl: str = "llama_cpp"  # "llama_cpp", "ollama", "ctranslate2", "transformers"


class InferenceRegistry:
    """
    Registry for LLM inference backends.
    Selects model based on requested model ID in OpenAI-compatible format.
    Supports multiple backend implementations per model type.
    """
    
    def __init__(self):
        self.backends: Dict[ModelType, Any] = {}
        self.configs: Dict[ModelType, ModelConfig] = {}
        self._default_model: ModelType = ModelType.HARDWARELESS_CORE
        self._init_configs()
    
    def _init_configs(self):
        """Initialize default model configurations from environment."""
        # Hardwareless Core (hypervector pipeline)
        self.configs[ModelType.HARDWARELESS_CORE] = ModelConfig(
            model_type=ModelType.HARDWARELESS_CORE,
            name="Hardwareless Core",
            path="",
            enabled=True,
            priority=1,
            backend_impl="core"
        )
        
        # Qwen2.5-7B — configurable backend via QWEN_BACKEND env var
        qwen_backend = os.getenv("QWEN_BACKEND", "llama_cpp")
        qwen_path = os.getenv("QWEN_MODEL_PATH", "models/model.gguf")
        self.configs[ModelType.QWEN2_5_7B] = ModelConfig(
            model_type=ModelType.QWEN2_5_7B,
            name="Qwen2.5-7B Code Writer",
            path=qwen_path,
            device=os.getenv("QWEN_DEVICE", "cpu"),
            compute_type=os.getenv("QWEN_COMPUTE_TYPE", "int8"),
            enabled=os.getenv("QWEN_ENABLED", "1") == "1",
            priority=2,
            backend_impl=qwen_backend
        )
    
    def register_backend(self, model_type: ModelType, backend: Any):
        """Register an initialized backend instance."""
        self.backends[model_type] = backend
    
    def get_backend(self, model_id: str) -> Any:
        """
        Get backend for given model ID (OpenAI model field).
        Returns None if model not found or disabled.
        """
        try:
            model_type = ModelType(model_id)
        except ValueError:
            return None
        
        config = self.configs.get(model_type)
        if not config or not config.enabled:
            return None
        
        return self.backends.get(model_type)
    
    def get_config(self, model_type: ModelType) -> Optional[ModelConfig]:
        """Get configuration for a model type."""
        return self.configs.get(model_type)
    
    def list_models(self) -> List[Dict[str, Any]]:
        """
        List available models in OpenAI format.
        """
        models = []
        for model_type, config in self.configs.items():
            if config.enabled and model_type in self.backends:
                models.append({
                    "id": model_type.value,
                    "object": "model",
                    "created": int(os.path.getctime(config.path) if os.path.exists(config.path) else int(time.time())),
                    "owned_by": "hardwareless-ai" if model_type == ModelType.HARDWARELESS_CORE else "qwen",
                    "permission": [],
                    "root": model_type.value,
                    "parent": None,
                })
        return models
    
    def set_default_model(self, model_type: ModelType):
        self._default_model = model_type
    
    def get_default_model(self) -> ModelType:
        return self._default_model


_global_registry: Optional[InferenceRegistry] = None


def get_inference_registry() -> InferenceRegistry:
    """Get or create the global inference registry."""
    global _global_registry
    if _global_registry is None:
        _global_registry = InferenceRegistry()
    return _global_registry
