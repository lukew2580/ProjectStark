"""
Hardwareless AI — Memory API Routes
Persistent conversation history for users
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import json
import os
from pathlib import Path

router = APIRouter(prefix="/v1/memory", tags=["memory"])

MEMORY_DIR = Path("memory/conversations")
MEMORY_DIR.mkdir(parents=True, exist_ok=True)


class ConversationMessage(BaseModel):
    role: str
    content: str
    metadata: Optional[Dict[str, Any]] = None


class SaveConversationRequest(BaseModel):
    user_id: str
    conversation_id: str
    messages: List[ConversationMessage]
    metadata: Optional[Dict[str, Any]] = None


class GetConversationRequest(BaseModel):
    user_id: str
    conversation_id: str


class ListConversationsRequest(BaseModel):
    user_id: str
    limit: int = 20


def _get_conversation_path(user_id: str, conversation_id: str) -> Path:
    user_dir = MEMORY_DIR / user_id
    user_dir.mkdir(exist_ok=True)
    return user_dir / f"{conversation_id}.json"


@router.post("/save")
async def save_conversation(request: SaveConversationRequest):
    """Save a conversation to disk."""
    path = _get_conversation_path(request.user_id, request.conversation_id)
    
    data = {
        "conversation_id": request.conversation_id,
        "messages": [msg.dict() for msg in request.messages],
        "metadata": request.metadata or {}
    }
    
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    
    return {"status": "saved", "conversation_id": request.conversation_id}


@router.post("/get")
async def get_conversation(request: GetConversationRequest):
    """Retrieve a conversation."""
    path = _get_conversation_path(request.user_id, request.conversation_id)
    
    if not path.exists():
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    with open(path, "r") as f:
        data = json.load(f)
    
    return data


@router.post("/list")
async def list_conversations(request: ListConversationsRequest):
    """List all conversations for a user."""
    user_dir = MEMORY_DIR / request.user_id
    
    if not user_dir.exists():
        return {"conversations": []}
    
    conversations = []
    for f in user_dir.glob("*.json"):
        with open(f, "r") as fp:
            data = json.load(fp)
            conversations.append({
                "conversation_id": data.get("conversation_id"),
                "message_count": len(data.get("messages", [])),
                "metadata": data.get("metadata", {})
            })
    
    conversations.sort(key=lambda x: x.get("message_count", 0), reverse=True)
    return {"conversations": conversations[:request.limit]}


@router.delete("/delete")
async def delete_conversation(request: GetConversationRequest):
    """Delete a conversation."""
    path = _get_conversation_path(request.user_id, request.conversation_id)
    
    if not path.exists():
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    path.unlink()
    
    return {"status": "deleted", "conversation_id": request.conversation_id}


@router.post("/append")
async def append_message(request: GetConversationRequest, message: ConversationMessage):
    """Append a message to an existing conversation."""
    path = _get_conversation_path(request.user_id, request.conversation_id)
    
    if path.exists():
        with open(path, "r") as f:
            data = json.load(f)
    else:
        data = {"conversation_id": request.conversation_id, "messages": [], "metadata": {}}
    
    data["messages"].append(message.dict())
    
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    
    return {"status": "appended", "message_count": len(data["messages"])}