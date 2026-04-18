"""
Hardwareless AI — Pluggable HDC Backend System

Architecture:
-----------
1. HDBackend ( Protocol/Interface )
   - generate(dim, seed) -> np.ndarray
   - bind(a, b) -> np.ndarray
   - bundle(vectors, dim) -> np.ndarray
   - permute(vec, shifts) -> np.ndarray
   - similarity(a, b, dim) -> float
   - name: str
   - description: str
   - capabilities: dict

2. Backend Registry
   - register(name, backend)
   - get(name) -> HDBackend
   - list() -> [names]
   - set_active(name)
   - get_active() -> HDBackend

3. Backend Implementations
   - LegacyNumpyBackend (current custom HDC)
   - TorchHDBackend (new, GPU-accelerated)
   - HBLLMBackend (future: cognitive architecture)
   - CustomBackend (user-provided)

4. Environment Configuration
   HDC_BACKEND=legacy|torchhd|hbllm
   HDC_BACKEND_ARGS=... (JSON)
"""
from typing import Protocol, Optional, Tuple, Any, Dict
import numpy as np
from abc import ABC, abstractmethod

# Type definitions
Vector = np.ndarray  # shape: (dimensions,), dtype: int8 or float32


class HDBackend(Protocol):
    """Protocol for pluggable HDC backends."""

    def generate(self, dimensions: int, seed: Optional[int] = None, **kwargs: Any) -> Vector:
        """Generate a random hypervector."""
        ...

    def bind(self, vec_a: Vector, vec_b: Vector) -> Vector:
        """Bind two vectors (association)."""
        ...

    def bundle(self, vectors: list[Vector], dimensions: int, **kwargs: Any) -> Vector:
        """Bundle multiple vectors into a set."""
        ...

    def permute(self, vec: Vector, shifts: int = 1) -> Vector:
        """Permute vector to encode order/position."""
        ...

    def similarity(self, vec_a: Vector, vec_b: Vector, dimensions: int) -> float:
        """Compute cosine similarity between vectors."""
        ...

    @property
    def name(self) -> str:
        """Backend identifier."""
        ...

    @property
    def description(self) -> str:
        """Human-readable description."""
        ...

    @property
    def capabilities(self) -> Dict[str, Any]:
        """Backend capabilities and features."""
        ...


# ============================================================================
# LEGACY BACKEND — Your current custom HDC implementation
# ============================================================================

class LegacyNumpyBackend:
    """
    Original HDC implementation (numpy-based, pure Python).
    
    Characteristics:
      - Deterministic, fully controllable
      - CPU-only, no GPU acceleration
      - Bipolar vectors (-1, +1) with int8 storage
      - Simple, transparent operations
    """
    def __init__(self, rng: Optional[np.random.Generator] = None):
        self._rng = rng or np.random.default_rng()

    def generate(self, dimensions: int, seed: Optional[int] = None, **kwargs: Any) -> Vector:
        if seed is not None:
            rng = np.random.default_rng(seed)
        else:
            rng = self._rng
        bits = rng.integers(0, 2, size=dimensions, dtype=np.uint8)
        return np.where(bits, np.int8(1), np.int8(-1))

    def bind(self, vec_a: Vector, vec_b: Vector) -> Vector:
        return (vec_a * vec_b).astype(np.int8)

    def bundle(self, vectors: list[Vector], dimensions: int, **kwargs: Any) -> Vector:
        if not vectors:
            return np.zeros(dimensions, dtype=np.int8)
        stacked = np.stack(vectors)
        summed = stacked.sum(axis=0)
        ties = (summed == 0)
        result = np.where(summed > 0, np.int8(1), np.int8(-1))
        if ties.any():
            tie_breaks = self.generate(dimensions)
            result[ties] = tie_breaks[ties]
        return result

    def permute(self, vec: Vector, shifts: int = 1) -> Vector:
        return np.roll(vec, shifts).astype(np.int8)

    def similarity(self, vec_a: Vector, vec_b: Vector, dimensions: int) -> float:
        return float(np.dot(vec_a.astype(np.int32), vec_b.astype(np.int32))) / dimensions

    @property
    def name(self) -> str:
        return "legacy-numpy"

    @property
    def description(self) -> str:
        return "Original custom HDC implementation (numpy, CPU-only)"

    @property
    def capabilities(self) -> Dict[str, Any]:
        return {
            "gpu": False,
            "vector_type": "bipolar",
            "dtype": "int8",
            "operators": ["bind", "bundle", "permute", "similarity"],
            "dimension_range": (100, 100000),
            "thread_safe": True,
        }


# ============================================================================
# TORCHHD BACKEND — GPU-accelerated, multi-model VSA library
# ============================================================================

class TorchHDBackend:
    """
    Backend using the torchhd library (UC Irvine).
    
    Features:
      - GPU-accelerated via PyTorch
      - Multiple VSA models: MAP, BSC, HRR, FHRR, etc.
      - Automatic differentiation support
      - 100×+ faster than pure numpy
    
    Install: pip install torchhd torch
    """
    def __init__(self, model: str = "MAP", dimensions: int = 10000, device: str = "cpu"):
        try:
            import torchhd
        except ImportError:
            raise ImportError(
                "torchhd not installed. Run: pip install torchhd torch\n"
                "See: https://github.com/hyperdimensional-computing/torchhd"
            )
        
        self._torchhd = torchhd
        self._device = device
        self._model_type = model
        self._dimensions = dimensions
        
        # Initialize the VSA model
        if model == "MAP":
            self._vsa = torchhd.models.MAP(dimensions=dimensions, device=device)
        elif model == "BSC":
            self._vsa = torchhd.models.BSC(dimensions=dimensions, device=device)
        elif model == "HRR":
            self._vsa = torchhd.models.HRR(dimensions=dimensions, device=device)
        elif model == "FHRR":
            self._vsa = torchhd.models.FHRR(dimensions=dimensions, device=device)
        else:
            raise ValueError(f"Unsupported torchhd model: {model}")
    
    def _to_tensor(self, vec: Vector) -> "torchhd.VSA":
        """Convert numpy vector to torchhd tensor."""
        import torch
        # torchhd expects float tensors in range [-1, 1] for some models
        tensor = torch.from_numpy(vec.astype(np.float32))
        if self._device == "cuda":
            tensor = tensor.cuda()
        return self._vsa.from_vector(tensor)
    
    def _to_numpy(self, vsa_obj) -> Vector:
        """Convert torchhd VSA object back to numpy."""
        vec = vsa_obj.vector.cpu().numpy() if hasattr(vsa_obj, 'vector') else np.array(vsa_obj)
        return vec.astype(np.int8) if vec.dtype == np.float32 else vec

    def generate(self, dimensions: int, seed: Optional[int] = None, **kwargs: Any) -> Vector:
        import torch
        if seed is not None:
            torch.manual_seed(seed)
        # torchhd uses float vectors; convert to bipolar int8 for compatibility
        hv = self._vsa.random()
        result = self._to_numpy(hv)
        # Ensure bipolar (-1, 1) if needed
        if result.dtype != np.int8:
            result = np.where(result > 0, 1, -1).astype(np.int8)
        return result

    def bind(self, vec_a: Vector, vec_b: Vector) -> Vector:
        hv_a = self._to_tensor(vec_a)
        hv_b = self._to_tensor(vec_b)
        bound = self._vsa.bind(hv_a, hv_b)
        result = self._to_numpy(bound)
        return result.astype(np.int8)

    def bundle(self, vectors: list[Vector], dimensions: int, **kwargs: Any) -> Vector:
        if not vectors:
            return np.zeros(dimensions, dtype=np.int8)
        hv_list = [self._to_tensor(v) for v in vectors]
        bundled = self._vsa.bundle(hv_list)
        result = self._to_numpy(bundled)
        return result.astype(np.int8)

    def permute(self, vec: Vector, shifts: int = 1) -> Vector:
        hv = self._to_tensor(vec)
        # torchhd permute is cyclic shift
        permuted = self._vsa.permute(hv, shifts=shifts)
        result = self._to_numpy(permuted)
        return result.astype(np.int8)

    def similarity(self, vec_a: Vector, vec_b: Vector, dimensions: int) -> float:
        hv_a = self._to_tensor(vec_a)
        hv_b = self._to_tensor(vec_b)
        # torchhd similarity is cosine on [-1,1] space
        sim = self._vsa.similarity(hv_a, hv_b)
        return float(sim)

    @property
    def name(self) -> str:
        return f"torchhd-{self._model_type}"

    @property
    def description(self) -> str:
        return f"TorchHD {self._model_type} model (GPU={self._device != 'cpu'})"

    @property
    def capabilities(self) -> Dict[str, Any]:
        return {
            "gpu": self._device != "cpu",
            "vector_type": "bipolar" if self._model_type in ["MAP", "BSC"] else "complex",
            "dtype": "float32" if self._device == "cpu" else "cuda",
            "operators": ["bind", "bundle", "permute", "similarity"],
            "dimension_range": (1024, 2**20),  # torchhd supports up to 2^20
            "thread_safe": False,  # PyTorch has GIL concerns
            "model": self._model_type,
        }


# ============================================================================
# BACKEND REGISTRY — Singleton manager
# ============================================================================

class BackendRegistry:
    """Registry and factory for HDC backends."""
    _instance: Optional['BackendRegistry'] = None
    _backends: Dict[str, HDBackend] = {}
    _active_name: str = ""

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def register(self, name: str, backend: HDBackend) -> None:
        """Register a backend."""
        self._backends[name] = backend

    def get(self, name: str) -> HDBackend:
        """Get a backend by name."""
        if name not in self._backends:
            raise KeyError(f"Backend '{name}' not registered. Available: {list(self._backends.keys())}")
        return self._backends[name]

    def set_active(self, name: str) -> None:
        """Set the currently active backend."""
        if name not in self._backends:
            raise KeyError(f"Backend '{name}' not registered")
        self._active_name = name

    @property
    def active(self) -> HDBackend:
        """Get the currently active backend."""
        if not self._active_name:
            raise RuntimeError("No active backend. Call set_active() first.")
        return self._backends[self._active_name]

    def list_backends(self) -> list[Dict[str, Any]]:
        """List all registered backends with metadata."""
        return [
            {
                "name": name,
                "description": backend.description,
                "capabilities": backend.capabilities,
            }
            for name, backend in self._backends.items()
        ]

    def autodetect(self, prefer_gpu: bool = True) -> str:
        """Auto-select best available backend."""
        # Preference order:
        # 1. TorchHD with CUDA (if GPU available and prefer_gpu)
        # 2. TorchHD CPU
        # 3. Legacy numpy
        if prefer_gpu:
            try:
                import torch
                if torch.cuda.is_available():
                    self.register("torchhd-cuda", TorchHDBackend(device="cuda"))
                    return "torchhd-cuda"
            except ImportError:
                pass
        
        try:
            import torchhd
            self.register("torchhd-cpu", TorchHDBackend(device="cpu"))
            return "torchhd-cpu"
        except ImportError:
            pass
        
        # Fall back to legacy
        self.register("legacy", LegacyNumpyBackend())
        return "legacy"


# Global registry instance
_registry = BackendRegistry()


def get_backend(name: Optional[str] = None) -> HDBackend:
    """
    Get the current HDC backend.
    
    Usage:
        backend = get_backend()  # active
        backend = get_backend("torchhd-cpu")  # specific
    """
    if name is None:
        return _registry.active
    return _registry.get(name)


def register_backend(name: str, backend: HDBackend) -> None:
    """Register a custom backend."""
    _registry.register(name, backend)


def set_active_backend(name: str) -> None:
    """Switch the active backend."""
    _registry.set_active(name)


# ============================================================================
# DEFAULT INITIALIZATION — Auto-detect on first import
# ============================================================================

def initialize_backends() -> str:
    """Initialize and auto-select best backend. Called on first use."""
    selected = _registry.autodetect(prefer_gpu=True)
    set_active_backend(selected)
    return selected
