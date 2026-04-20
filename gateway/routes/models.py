"""
Hardwareless AI — OpenAI Models Endpoint
"""
import time
from fastapi import APIRouter
from core_engine.inference import get_inference_registry

router = APIRouter()

@router.get("/v1/models")
async def list_models():
    """Returns the available models in standard OpenAI format."""
    inference_registry = get_inference_registry()
    models = inference_registry.list_models()
    
    return {
        "object": "list",
        "data": models
    }
