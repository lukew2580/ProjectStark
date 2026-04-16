"""
Hardwareless AI — WebSocket Real-time Routes
Streaming responses for real-time interaction
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, Any, Optional
import asyncio
import json

router = APIRouter(tags=["websocket"])


class ConnectionManager:
    """Manages WebSocket connections."""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
    
    def disconnect(self, client_id: str):
        self.active_connections.pop(client_id, None)
    
    async def send_message(self, client_id: str, message: dict):
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_json(message)
    
    async def broadcast(self, message: dict):
        for connection in self.active_connections.values():
            await connection.send_json(message)


manager = ConnectionManager()


@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """
    WebSocket chat endpoint for real-time streaming.
    
    Send: {"type": "message", "content": "your text", "user_id": "xxx"}
    Receive: {"type": "chunk", "content": "..."} or {"type": "done", "result": "..."}
    """
    client_id = None
    
    try:
        while True:
            data = await websocket.receive_json()
            
            if data.get("type") == "init":
                client_id = data.get("user_id", "anonymous")
                await manager.connect(websocket, client_id)
                await manager.send_message(client_id, {
                    "type": "connected",
                    "client_id": client_id
                })
            
            elif data.get("type") == "message":
                if not client_id:
                    client_id = data.get("user_id", "anonymous")
                    await manager.connect(websocket, client_id)
                
                content = data.get("content", "")
                user_id = data.get("user_id", "anonymous")
                
                await manager.send_message(client_id, {
                    "type": "processing"
                })
                
                from core_engine.translation import get_weave
                weave = get_weave()
                
                result = await weave.think(
                    input_text=content,
                    target_lang="en"
                )
                
                await manager.send_message(client_id, {
                    "type": "done",
                    "result": result.target_text,
                    "source_lang": result.source_lang,
                    "confidence": result.confidence
                })
            
            elif data.get("type") == "ping":
                await manager.send_message(client_id, {"type": "pong"})
    
    except WebSocketDisconnect:
        if client_id:
            manager.disconnect(client_id)
    except Exception as e:
        if client_id:
            await manager.send_message(client_id, {
                "type": "error",
                "error": str(e)
            })
            manager.disconnect(client_id)


@router.websocket("/ws/stream")
async def websocket_stream(websocket: WebSocket):
    """
    WebSocket for streaming /v1/chat/completions style responses.
    """
    client_id = None
    
    try:
        while True:
            data = await websocket.receive_json()
            
            if data.get("type") == "init":
                client_id = data.get("user_id", "anonymous")
                await manager.connect(websocket, client_id)
            
            elif data.get("type") == "chat":
                messages = data.get("messages", [])
                model = data.get("model", "hardwareless-core")
                
                last_message = messages[-1].get("content", "") if messages else ""
                
                await manager.send_message(client_id, {
                    "type": "chunk",
                    "delta": "🤖 "
                })
                
                from core_engine.translation import get_weave
                weave = get_weave()
                
                result = await weave.think(
                    input_text=last_message,
                    target_lang="en"
                )
                
                words = result.target_text.split()
                for word in words:
                    await manager.send_message(client_id, {
                        "type": "chunk",
                        "delta": word + " "
                    })
                    await asyncio.sleep(0.05)
                
                await manager.send_message(client_id, {
                    "type": "done",
                    "finish_reason": "stop"
                })
    
    except WebSocketDisconnect:
        if client_id:
            manager.disconnect(client_id)


@router.websocket("/ws/translate")
async def websocket_translate(websocket: WebSocket):
    """WebSocket for real-time translation streaming."""
    client_id = None
    
    try:
        while True:
            data = await websocket.receive_json()
            
            if data.get("type") == "init":
                client_id = data.get("user_id", "anonymous")
                await manager.connect(websocket, client_id)
            
            elif data.get("type") == "translate":
                text = data.get("text", "")
                target_lang = data.get("target_lang", "en")
                
                from core_engine.translation import get_weave
                weave = get_weave()
                
                result = await weave.think(
                    input_text=text,
                    target_lang=target_lang
                )
                
                await manager.send_message(client_id, {
                    "type": "translated",
                    "original": text,
                    "translated": result.target_text,
                    "source_lang": result.source_lang,
                    "target_lang": result.target_lang
                })
    
    except WebSocketDisconnect:
        if client_id:
            manager.disconnect(client_id)