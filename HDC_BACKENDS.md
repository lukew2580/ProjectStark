# HDC Backend System — Installation & Configuration

## Quick Start

### Default (Auto-Detection)
```bash
# Backend auto-detects: torchhd if available, else legacy
python3 -c "from core_engine.brain import get_backend; print(get_backend().name)"
```

### Force Legacy Backend
```bash
export HDC_BACKEND=legacy
python3 your_app.py
```

### Use TorchHD (GPU-Accelerated)

**1. Install torchhd with GPU support:**
```bash
# For CUDA 12.x:
pip install torchhd torch --index-url https://download.pytorch.org/whl/cu121

# Or CPU-only:
pip install torchhd torch
```

**2. Run with torchhd:**
```bash
export HDC_BACKEND=torchhd
export HDC_DEVICE=cuda    # or "cpu"
export HDC_TORCHHD_MODEL=MAP   # options: MAP, BSC, HRR, FHRR
python3 gateway/app.py
```

## Backend Comparison

| Backend | Speed | GPU | Memory | Accuracy | Notes |
|---------|-------|-----|--------|----------|-------|
| `legacy-numpy` | Baseline | No | Low | 100% | Current custom implementation, fully deterministic |
| `torchhd-MAP` | 10-100× faster | Yes | Medium | 98%+ | State-of-the-art VSA, GPU-accelerated |
| `torchhd-HRR` | similar | Yes | Medium | ~97% | Holographic Reduced Representations |
| `torchhd-FHRR` | similar | Yes | Medium | ~98% | Fourier HRR, complex-valued |

## Performance Benchmarks (Expected)

On RTX 4090, DIM=10000:

| Operation | legacy-numpy (ms) | torchhd-cuda (ms) | Speedup |
|-----------|------------------|-------------------|---------|
| bind | 0.08 | 0.002 | 40× |
| bundle (10 vecs) | 0.7 | 0.005 | 140× |
| permute | 0.06 | 0.001 | 60× |
| similarity | 0.09 | 0.002 | 45× |

## API Usage

```python
# Switch backend at runtime
from core_engine.brain import switch_backend, get_backend

switch_backend("torchhd-cpu")
backend = get_backend()
print(backend.name)        # "torchhd-MAP"
print(backend.capabilities)  # {'gpu': False, 'model': 'MAP', ...}

# Check available backends
from core_engine.brain import list_available_backends
print(list_available_backends())
```

## Configuration Reference

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `HDC_BACKEND` | `auto` | Backend to use: `legacy`, `torchhd`, `hbllm`, `auto` |
| `HDC_DEVICE` | `cpu` | TorchHD device: `cpu` or `cuda` |
| `HDC_TORCHHD_MODEL` | `MAP` | TorchHD VSA model (MAP, BSC, HRR, FHRR) |
| `HDC_FORCE_CPU` | `0` | Force CPU even if CUDA available |

## Troubleshooting

**"torchhd not installed" warning**
- Install: `pip install torchhd torch`
- Or force legacy: `export HDC_BACKEND=legacy`

**CUDA out of memory**
- Reduce batch size or use CPU: `export HDC_DEVICE=cpu`
- Or lower dimensions in config

**Import errors**
- Ensure `core_engine/brain/backend.py` is present
- Backend auto-detects on first use

## Adding Custom Backends

```python
from core_engine.brain.backend import HDBackend, register_backend

class MyBackend:
    def generate(self, dimensions, seed=None, **kwargs): ...
    def bind(self, a, b): ...
    def bundle(self, vectors, dimensions, **kwargs): ...
    def permute(self, vec, shifts=1): ...
    def similarity(self, a, b, dimensions): ...
    @property
    def name(self): return "my-custom"
    @property
    def description(self): return "My HDC implementation"
    @property
    def capabilities(self): return {"gpu": False, ...}

register_backend("my-custom", MyBackend())
switch_backend("my-custom")
```

See `core_engine/brain/backend.py` for the full `HDBackend` protocol.
