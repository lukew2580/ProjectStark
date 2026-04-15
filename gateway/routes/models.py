"""
Hardwareless AI — OpenAI Models Endpoint
"""
import time
from fastapi import APIRouter

router = APIRouter()

@router.get("/v1/models")
async def list_models():
    """Returns the available models in standard OpenAI format."""
    return {
        "object": "list",
        "data": [
            {
                "id": "hardwareless-core",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "hardwareless-ai",
                "permission": [],
                "root": "hardwareless-core",
                "parent": None,
            }
        ]
    }
