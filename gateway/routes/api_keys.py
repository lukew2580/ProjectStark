"""
Hardwareless AI — API Key Management Routes
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional

from gateway.middleware.auth import get_api_key_manager

router = APIRouter(prefix="/v1/keys", tags=["API Keys"])


class CreateKeyRequest(BaseModel):
    name: str
    rate_limit: int = 100
    scopes: List[str] = ["read"]


class CreateKeyResponse(BaseModel):
    key: str
    name: str
    scopes: List[str]
    rate_limit: int


class KeyInfo(BaseModel):
    name: str
    scopes: List[str]
    rate_limit: int


@router.post("/", response_model=CreateKeyResponse)
async def create_api_key(request: CreateKeyRequest):
    """Create new API key."""
    manager = get_api_key_manager()
    key = manager.create_key(request.name, request.rate_limit, request.scopes)
    
    return CreateKeyResponse(
        key=key,
        name=request.name,
        scopes=request.scopes,
        rate_limit=request.rate_limit
    )


@router.get("/", response_model=List[KeyInfo])
async def list_keys():
    """List all API keys."""
    manager = get_api_key_manager()
    return manager.list_keys()


@router.delete("/{key_name}")
async def revoke_key(key_name: str):
    """Revoke API key by name."""
    manager = get_api_key_manager()
    
    for key, info in manager._keys.items():
        if info["name"] == key_name:
            manager.revoke_key(info["key"])
            return {"status": "revoked", "name": key_name}
    
    raise HTTPException(status_code=404, detail="Key not found")