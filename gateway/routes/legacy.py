"""
Legacy Compatibility Routes
Provides backward-compatible endpoints for the original frontend while new frontend migrates to v1 API.
"""
import asyncio
import json
from typing import Optional
from fastapi import APIRouter, Request, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field
from core_engine.translation.encoder import Encoder
from core_engine.translation.decoder import Decoder
from core_engine.pipeline.pipeline import DataFlowPipeline
from config.settings import DIMENSIONS, KNOWLEDGE_BASE, DEFAULT_NODE_COUNT
from core_engine.compression.compressor import CognitiveCompressor
from core_engine.security.validator import get_validator, get_audit_logger
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=10000)

class ChatResponse(BaseModel):
    response: str

@router.post("/chat")
async def legacy_chat(req: ChatRequest, request: Request):
    """
    Legacy chat endpoint: POST /chat with {question: "..."}
    Returns: {response: "..."}
    Internally routes to v1 chat completion.
    """
    try:
        # Audit log
        validator = get_validator()
        audit = get_audit_logger()
        audit.log("legacy_chat", {"question_length": len(req.question), "client": request.client.host if request.client else "unknown"})

        # Use the new chat pipeline (same as v1 but wrapped)
        compressor = CognitiveCompressor()
        encoder = Encoder()
        decoder = Decoder()
        pipeline = DataFlowPipeline()

        # Compress
        compressed = compressor.compress(req.question)

        # Encode to hypervector
        vector = encoder.encode(compressed)

        # Process through pipeline
        result = pipeline.process(vector)

        # Decode
        answer = decoder.decode(result)

        return {"response": answer}
    except Exception as e:
        logger.error(f"Legacy chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Swarm processing error")

@router.websocket("/ws/stream")
async def legacy_websocket_stream(websocket: WebSocket):
    """
    Legacy WebSocket streaming endpoint: ws://localhost:8000/ws/stream
    Protocol: send {"type": "chat", "messages": [{"role": "user", "content": "..."}]}
    Receives: {"type": "chunk", "delta": "..."} and {"type": "done"}
    """
    await websocket.accept()
    try:
        # Wait for init
        init_data = await websocket.receive_json()
        if init_data.get("type") != "init":
            await websocket.close(code=1003)
            return

        # Send ready
        await websocket.send_json({"type": "ready"})

        while True:
            msg = await websocket.receive_json()
            if msg.get("type") != "chat":
                continue

            user_content = msg.get("messages", [{}])[0].get("content", "")
            if not user_content:
                continue

            # Stream response using the same logic as SSE but over WebSocket
            try:
                compressor = CognitiveCompressor()
                encoder = Encoder()
                decoder = Decoder()
                pipeline = DataFlowPipeline()

                compressed = compressor.compress(user_content)
                vector = encoder.encode(compressed)
                result = pipeline.process(vector)

                # Decode and stream word-by-word (simulated streaming)
                answer = decoder.decode(result)
                words = answer.split()

                for i, word in enumerate(words):
                    await websocket.send_json({
                        "type": "chunk",
                        "delta": word + (" " if i < len(words) - 1 else "")
                    })
                    await asyncio.sleep(0.02)  # simulate streaming delay

                await websocket.send_json({"type": "done"})
            except Exception as e:
                logger.error(f"Stream error: {e}")
                await websocket.send_json({"type": "error", "error": str(e)})

    except WebSocketDisconnect:
        logger.info("Legacy WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close()
