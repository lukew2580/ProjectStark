"""
Hardwareless AI — Keys API Routes
User-supplied API key management
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict

router = APIRouter(prefix="/v1/keys", tags=["keys"])


class SetKeysRequest(BaseModel):
    user_id: str
    openai_key: Optional[str] = None
    anthropic_key: Optional[str] = None
    google_key: Optional[str] = None
    deepseek_key: Optional[str] = None
    custom_keys: Optional[Dict[str, str]] = None


class CheckKeysRequest(BaseModel):
    user_id: str


class ClearKeysRequest(BaseModel):
    user_id: str


@router.post("/set")
async def set_user_keys(request: SetKeysRequest):
    """Set user's API keys (user supplies their own)."""
    from core_engine.api_keys import UserAPIKeys, get_key_manager
    
    keys = UserAPIKeys(
        openai_key=request.openai_key,
        anthropic_key=request.anthropic_key,
        google_key=request.google_key,
        deepseek_key=request.deepseek_key,
        custom_keys=request.custom_keys
    )
    
    manager = get_key_manager()
    manager.set_keys(request.user_id, keys)
    
    return {
        "status": "set",
        "user_id": request.user_id,
        "keys": keys.to_dict()
    }


@router.post("/check")
async def check_keys(request: CheckKeysRequest):
    """Check which providers a user has configured."""
    from core_engine.api_keys import get_key_manager
    
    manager = get_key_manager()
    status = manager.check_key_status(request.user_id)
    
    return status


@router.post("/clear")
async def clear_keys(request: ClearKeysRequest):
    """Clear user's API keys."""
    from core_engine.api_keys import get_key_manager
    
    manager = get_key_manager()
    manager.clear_keys(request.user_id)
    
    return {"status": "cleared", "user_id": request.user_id}


@router.get("/providers")
async def list_providers():
    """List available API providers."""
    return {
        "providers": [
            {"id": "openai", "name": "OpenAI", "models": ["gpt-4", "gpt-3.5-turbo"]},
            {"id": "anthropic", "name": "Anthropic", "models": ["claude-3-opus", "claude-3-sonnet"]},
            {"id": "google", "name": "Google", "models": ["gemini-pro", "gemini-ultra"]},
            {"id": "deepseek", "name": "DeepSeek", "models": ["deepseek-chat"]},
        ],
        "note": "Users supply their own API keys. We don't provide keys."
    }