"""
Hardwareless AI — Vector Visualization Endpoint
Returns downsampled hypervector data for frontend visualization.
"""
from fastapi import APIRouter, HTTPException
from core_engine.translation.encoder import Encoder
from config.settings import DIMENSIONS

router = APIRouter()

# Shared encoder instance (same as chat route)
_encoder = Encoder(dimensions=DIMENSIONS)


@router.get("/v1/vector")
async def get_vector(text: str, samples: int = 200):
    """
    Get a downsampled hypervector for visualization.
    
    Args:
        text: Input text to encode
        samples: Number of vector elements to return (max 1000)
    
    Returns:
        { vector: [...], text: str, total_dim: int, samples_shown: int }
    """
    if not text or not text.strip():
        raise HTTPException(400, "text query parameter is required")
    
    # Encode text to hypervector
    vector = _encoder.encode(text.strip())
    
    # Downsample: take evenly spaced elements to stay within browser rendering limits
    total_dim = len(vector)
    if samples >= total_dim:
        samples = total_dim
    
    step = max(1, total_dim // samples)
    sampled = vector[::step][:samples].tolist()
    
    return {
        "vector": sampled,
        "text": text,
        "total_dim": total_dim,
        "samples_shown": len(sampled),
        "sampling_step": step
    }
