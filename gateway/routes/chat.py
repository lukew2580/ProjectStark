"""
Hardwareless AI — Chat Endpoint
Security-hardened with input validation, audit logging, anomaly detection.
"""
import time
import uuid
import asyncio
import json
from datetime import datetime
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from config.settings import DIMENSIONS, KNOWLEDGE_BASE, DEFAULT_NODE_COUNT, RESPONSE_TEMPLATES
from core_engine.compression.compressor import CognitiveCompressor
from core_engine.translation.encoder import Encoder
from core_engine.translation.decoder import Decoder
from core_engine.translation import get_weave, setup_translation_backends
from core_engine.pipeline.pipeline import DataFlowPipeline
from core_engine.security.validator import get_validator, get_audit_logger, get_anomaly_detector, SecurityLevel, SecurityEvent

router = APIRouter()

# Initialize components
compressor = CognitiveCompressor()
encoder = Encoder(dimensions=DIMENSIONS)
decoder = Decoder(encoder=encoder)
pipeline = DataFlowPipeline(node_count=DEFAULT_NODE_COUNT, dimensions=DIMENSIONS)

# Security modules
_validator = get_validator()
_audit = get_audit_logger()
_detector = get_anomaly_detector()

# Initialize translation brain weave (lazy, on-demand backend setup)
_weave = None


def _get_weave():
    global _weave
    if _weave is None:
        _weave = get_weave()
        setup_translation_backends(enable_mtranserver=False, enable_libretranslate=False, enable_opus_mt=False)
    return _weave


# Cognitive Bootstrap: Inoculate Swarm with Repo DNA
import os
if os.getenv("BOOTSTRAP_COGNITION") == "1":
    kb_path = "knowledge_preheat.json"
    if os.path.exists(kb_path):
        try:
            with open(kb_path, "r") as f:
                dna = json.load(f)
            count = encoder.bulk_ingest(dna)
            print(f"--- [COGNITIVE LOAD] Swarm inoculated with {count} repo-wide concepts ---")
        except Exception as e:
            print(f"--- [COGNITIVE ERROR] Bootstrap failed: {e} ---")

# Pre-warm vocabulary
for word in KNOWLEDGE_BASE:
    encoder.get_word_vector(word)


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)
    
    @validator('question')
    def validate_question(cls, v):
        is_valid, error = _validator.validate_question(v)
        if not is_valid:
            raise ValueError(f"Invalid input: {error}")
        return _validator.sanitize(v)


class OpenAIRequest(BaseModel):
    model: str = "hardwareless-core"
    messages: list[Message]
    
    @validator('messages')
    def validate_messages(cls, v):
        for msg in v:
            if not msg.content or len(msg.content) > 5000:
                raise ValueError("Invalid message content")
        return v


def _log_request(endpoint: str, client_ip: str, user_agent: str, details: dict):
    _audit.log_event(
        SecurityEvent(
            timestamp=datetime.utcnow().isoformat(),
            level=SecurityLevel.LOW,
            event_type=f"request.{endpoint}",
            client_ip=client_ip,
            user_agent=user_agent,
            details=details
        )
    )


@router.post("/chat")
async def simple_chat(request: ChatRequest, req: Request):
    client_ip = req.client.host if req.client else "unknown"
    user_agent = req.headers.get("user-agent", "")
    
    _log_request("chat", client_ip, user_agent, {"question_len": len(request.question)})
    
    anomaly = _detector.check_anomaly(len(request.question.encode()))
    # Record this request size for future anomaly analysis
    _detector.record_request(len(request.question.encode()))
    if anomaly:
        _audit.log_event(
            SecurityEvent(
                timestamp=datetime.utcnow().isoformat(),
                level=SecurityLevel.HIGH,
                event_type="anomaly_detected",
                client_ip=client_ip,
                user_agent=user_agent,
                details={"anomaly": anomaly, "size": len(request.question)}
            )
        )
    
    t_start = time.perf_counter()
    input_vector = encoder.encode(request.question)
    output_vector = await pipeline.process(input_vector)
    top_concepts = decoder.decode_top(output_vector, KNOWLEDGE_BASE, n=3)
    
    with open("config/knowledge/code_atoms.json", "r") as f:
        code_atoms = json.load(f)
    agent_proposal = decoder.synthesize_code(output_vector, code_atoms)
    
    sentinel_incidents = pipeline.sentinel.incidents_prevented
    safety_status = "SAFE" if sentinel_incidents == 0 else "NEUTRALIZED"

    response_text = f"Swarm Analysis: Detected semantic alignment with {', '.join(top_concepts)}."

    # Build response
    response_data = {
        "response": response_text,
        "proposal": agent_proposal if safety_status == "SAFE" else None,
        "sentinel_verification": safety_status
    }

    # Add anomaly header if detected
    headers = {}
    if anomaly:
        headers["X-Anomaly"] = "detected"
        headers["X-Anomaly-Type"] = anomaly

    return JSONResponse(content=response_data, headers=headers)


@router.post("/v1/chat/completions")
async def chat_completions(request: OpenAIRequest, req: Request):
    client_ip = req.client.host if req.client else "unknown"
    user_agent = req.headers.get("user-agent", "")
    
    raw_prompt = request.messages[-1].content
    
    if len(raw_prompt) > 5000:
        raise HTTPException(400, "Prompt too long (max 5000 chars)")
    
    _log_request("chat_completions", client_ip, user_agent, {"prompt_len": len(raw_prompt)})
    
    anomaly = _detector.check_anomaly(len(raw_prompt.encode()))
    # Record this request size for future anomaly analysis
    _detector.record_request(len(raw_prompt.encode()))
    if anomaly:
        _audit.log_event(
            SecurityEvent(
                timestamp=datetime.utcnow().isoformat(),
                level=SecurityLevel.HIGH,
                event_type="anomaly_detected",
                client_ip=client_ip,
                user_agent=user_agent,
                details={"anomaly": anomaly, "size": len(raw_prompt)}
            )
        )
    
    t_start = time.perf_counter()

    compressed_prompt = compressor.compress(raw_prompt)
    input_vector = encoder.encode(compressed_prompt)
    output_vector = await pipeline.process(input_vector)
    top_concepts = decoder.decode_top(output_vector, KNOWLEDGE_BASE, n=5)

    with open("config/knowledge/code_atoms.json", "r") as f:
        code_atoms = json.load(f)
    agent_proposal = decoder.synthesize_code(output_vector, code_atoms)
    
    sentinel_incidents = pipeline.sentinel.incidents_prevented
    safety_status = "SAFE" if sentinel_incidents == 0 else "NEUTRALIZED"

    elapsed_ms = (time.perf_counter() - t_start) * 1000
    template = RESPONSE_TEMPLATES[hash(raw_prompt) % len(RESPONSE_TEMPLATES)]
    response_text = template.format(
        concepts=", ".join(top_concepts),
        node_count=DEFAULT_NODE_COUNT,
        time_ms=f"{elapsed_ms:.2f}",
    )

    if agent_proposal and safety_status == "SAFE":
        response_text += f"\n\n--- [AGENTIC PROPOSAL] ---\n{agent_proposal}"
    elif safety_status == "NEUTRALIZED":
        response_text += f"\n\n[SENTINEL ALERT] A destructive code pattern was detected and neutralized."

    raw_words = len(raw_prompt.split())
    compressed_words = len(compressed_prompt.split()) if compressed_prompt else 0
    words_saved = raw_words - compressed_words

    response_data = {
        "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": request.model,
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": response_text,
            },
            "finish_reason": "stop"
        }],
        "usage": {
            "prompt_dimensions": compressed_words * DIMENSIONS,
            "completion_dimensions": DIMENSIONS,
            "total_dimensions": (compressed_words + 1) * DIMENSIONS,
            "compression": {
                "raw_words": raw_words,
                "compressed_words": compressed_words,
                "words_saved": words_saved,
                "ratio": f"{words_saved / max(raw_words, 1):.0%}",
            }
        }
    }

    # Add anomaly header if detected
    headers = {}
    if anomaly:
        headers["X-Anomaly"] = "detected"
        headers["X-Anomaly-Type"] = anomaly

    return JSONResponse(content=response_data, headers=headers)


class TranslateRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)
    source_lang: str = "auto"
    target_lang: str = "en"
    
    @validator('text')
    def validate_text(cls, v):
        is_valid, error = _validator.validate_translation_text(v)
        if not is_valid:
            raise ValueError(f"Invalid text: {error}")
        return _validator.sanitize(v)


@router.post("/translate")
async def translate(request: TranslateRequest, req: Request):
    """Multilingual translation via HDC brain weave + neural backends."""
    client_ip = req.client.host if req.client else "unknown"
    _log_request("translate", client_ip, req.headers.get("user-agent", ""), 
                 {"text_len": len(request.text), "src": request.source_lang, "tgt": request.target_lang})
    
    weave = _get_weave()
    
    result = await weave.think(
        input_text=request.text,
        input_lang=request.source_lang,
        target_lang=request.target_lang,
        polish=True
    )
    
    return {
        "original": request.text,
        "translated": result.target_text,
        "source_lang": result.source_lang,
        "target_lang": result.target_lang,
        "confidence": result.confidence,
        "hypervector_dim": result.hypervector.shape[0]
    }


@router.get("/languages")
async def list_languages():
    """List supported languages."""
    weave = _get_weave()
    return {
        "languages": weave.get_supported_languages(),
        "matrix_languages": get_weave().language_matrix.get_supported_languages(),
        "count": len(weave.language_matrix.get_supported_languages())
    }
