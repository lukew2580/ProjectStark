"""
Gateway — Batch API Endpoint
Process multiple translation/chat requests in a single HTTP call.
Reduces overhead for bulk operations.
"""

import time
import uuid
import asyncio
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
from pydantic import BaseModel, Field
import json

router = APIRouter(prefix="/v1/batch", tags=["batch"])


class BatchChatItem(BaseModel):
    id: Optional[str] = None
    question: str = Field(..., max_length=1000)
    model: Optional[str] = "hardwareless-core"


class BatchTranslateItem(BaseModel):
    id: Optional[str] = None
    text: str = Field(..., max_length=2000)
    source_lang: str = "auto"
    target_lang: str = "en"


class BatchRequest(BaseModel):
    operations: List[Dict[str, Any]]
    continue_on_error: bool = True  # If False, stop at first failure


class BatchResponse(BaseModel):
    results: List[Dict[str, Any]]
    success_count: int
    error_count: int
    total_ms: float


# Reuse existing components
from core_engine.translation.encoder import Encoder
from core_engine.translation.decoder import Decoder
from core_engine.pipeline.pipeline import DataFlowPipeline
from config.settings import DIMENSIONS, KNOWLEDGE_BASE, DEFAULT_NODE_COUNT
from core_engine.compression.compressor import CognitiveCompressor

compressor = CognitiveCompressor()
encoder = Encoder(dimensions=DIMENSIONS)
decoder = Decoder(encoder=encoder)
pipeline = DataFlowPipeline(node_count=DEFAULT_NODE_COUNT, dimensions=DIMENSIONS)


@router.post("/chat", response_model=BatchResponse)
async def batch_chat(request: BatchRequest, req: Request):
    """
    Process multiple /chat requests in one call.
    Input: {"operations": [{"question": "..."}, ...]}
    """
    start = time.perf_counter()
    
    if not request.operations:
        raise HTTPException(400, "No operations provided")
    
    if len(request.operations) > 100:
        raise HTTPException(400, "Max 100 operations per batch")
    
    results = []
    success = 0
    error = 0
    
    for op in request.operations:
        item_id = op.get("id", str(uuid.uuid4())[:8])
        question = op.get("question", "")
        
        try:
            # Validate
            if not question or len(question) > 1000:
                raise ValueError("Invalid question")
            
            # Process (similar to /chat endpoint)
            input_vector = encoder.encode(question)
            output_vector = await pipeline.process(input_vector)
            top_concepts = decoder.decode_top(output_vector, KNOWLEDGE_BASE, n=3)
            
            with open("config/knowledge/code_atoms.json") as f:
                code_atoms = json.load(f)
            agent_proposal = decoder.synthesize_code(output_vector, code_atoms)
            
            sentinel_incidents = pipeline.sentinel.incidents_prevented
            safety_status = "SAFE" if sentinel_incidents == 0 else "NEUTRALIZED"
            
            response_text = f"Swarm Analysis: Detected semantic alignment with {', '.join(top_concepts)}."
            
            result = {
                "id": item_id,
                "status": "success",
                "response": response_text,
                "proposal": agent_proposal if safety_status == "SAFE" else None,
                "sentinel_verification": safety_status,
            }
            results.append(result)
            success += 1
            
        except Exception as exc:
            if not request.continue_on_error:
                raise HTTPException(400, f"Batch failed at item {item_id}: {exc}")
            results.append({
                "id": item_id,
                "status": "error",
                "error": str(exc),
            })
            error += 1
    
    elapsed = (time.perf_counter() - start) * 1000
    
    return BatchResponse(
        results=results,
        success_count=success,
        error_count=error,
        total_ms=elapsed,
    )


@router.post("/translate", response_model=BatchResponse)
async def batch_translate(request: BatchRequest, req: Request):
    """
    Process multiple /translate requests in one call.
    Operations must include text, source_lang, target_lang.
    """
    start = time.perf_counter()
    
    if not request.operations:
        raise HTTPException(400, "No operations provided")
    
    # Lazy import to avoid startup cost
    from gateway.routes.chat import _get_weave
    
    weave = _get_weave()
    
    results = []
    success = 0
    error = 0
    
    semaphore = asyncio.Semaphore(10)  # Limit concurrent translations
    
    async def process_one(op):
        nonlocal success, error
        item_id = op.get("id", str(uuid.uuid4())[:8])
        text = op.get("text", "")
        src = op.get("source_lang", "auto")
        tgt = op.get("target_lang", "en")
        
        async with semaphore:
            try:
                result = await weave.think(
                    input_text=text,
                    input_lang=src,
                    target_lang=tgt,
                    polish=True,
                )
                results.append({
                    "id": item_id,
                    "status": "success",
                    "original": text,
                    "translated": result.target_text,
                    "source_lang": result.source_lang,
                    "target_lang": result.target_lang,
                    "confidence": result.confidence,
                    "dim": result.hypervector.shape[0],
                })
                success += 1
            except Exception as exc:
                if not request.continue_on_error:
                    raise
                results.append({
                    "id": item_id,
                    "status": "error",
                    "error": str(exc),
                })
                error += 1
    
    # Execute with limited concurrency
    tasks = [process_one(op) for op in request.operations]
    await asyncio.gather(*tasks, return_exceptions=False)
    
    elapsed = (time.perf_counter() - start) * 1000
    
    return BatchResponse(
        results=results,
        success_count=success,
        error_count=error,
        total_ms=elapsed,
    )


@router.get("/status")
async def batch_status():
    """Batch endpoint health and limits."""
    return {
        "max_operations": 100,
        "default_concurrency": 10,
        "supported_types": ["chat", "translate"],
    }
