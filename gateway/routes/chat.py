"""
Hardwareless AI — Chat Endpoint
"""
import time
import uuid
from fastapi import APIRouter
from pydantic import BaseModel
from config.settings import DIMENSIONS, KNOWLEDGE_BASE, DEFAULT_NODE_COUNT, RESPONSE_TEMPLATES
from core_engine.compression.compressor import CognitiveCompressor
from core_engine.translation.encoder import Encoder
from core_engine.translation.decoder import Decoder
from core_engine.pipeline.pipeline import DataFlowPipeline

router = APIRouter()

# Initialize components
compressor = CognitiveCompressor()
encoder = Encoder(dimensions=DIMENSIONS)
decoder = Decoder(encoder=encoder)
pipeline = DataFlowPipeline(node_count=DEFAULT_NODE_COUNT, dimensions=DIMENSIONS)

# Cognitive Bootstrap: Inoculate Swarm with Repo DNA
import os
import json
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
    question: str

@router.post("/chat")
async def simple_chat(request: ChatRequest):
    """Simple dashboard-compatible chat route."""
    t_start = time.perf_counter()
    input_vector = encoder.encode(request.question)
    output_vector = await pipeline.process(input_vector)
    top_concepts = decoder.decode_top(output_vector, KNOWLEDGE_BASE, n=3)
    
    # Load code atoms
    with open("config/knowledge/code_atoms.json", "r") as f:
        code_atoms = json.load(f)
    agent_proposal = decoder.synthesize_code(output_vector, code_atoms)
    
    sentinel_incidents = pipeline.sentinel.incidents_prevented
    safety_status = "SAFE" if sentinel_incidents == 0 else "NEUTRALIZED"

    response_text = f"Swarm Analysis: Detected semantic alignment with {', '.join(top_concepts)}."
    
    return {
        "response": response_text,
        "proposal": agent_proposal if safety_status == "SAFE" else None,
        "sentinel_verification": safety_status
    }

class OpenAIRequest(BaseModel):
    model: str = "hardwareless-core"
    messages: list[Message]

@router.post("/v1/chat/completions")
async def chat_completions(request: OpenAIRequest):
    raw_prompt = request.messages[-1].content
    t_start = time.perf_counter()

    compressed_prompt = compressor.compress(raw_prompt)
    input_vector = encoder.encode(compressed_prompt)
    output_vector = await pipeline.process(input_vector)
    top_concepts = decoder.decode_top(output_vector, KNOWLEDGE_BASE, n=5)

    # === AGENTIC PROPOSAL ===
    # Load code atoms for structural synthesis
    with open("config/knowledge/code_atoms.json", "r") as f:
        code_atoms = json.load(f)
    agent_proposal = decoder.synthesize_code(output_vector, code_atoms)
    
    # === SENTINEL VERIFICATION ===
    sentinel_incidents = pipeline.sentinel.incidents_prevented
    safety_status = "SAFE" if sentinel_incidents == 0 else "NEUTRALIZED"

    elapsed_ms = (time.perf_counter() - t_start) * 1000
    template = RESPONSE_TEMPLATES[hash(raw_prompt) % len(RESPONSE_TEMPLATES)]
    response_text = template.format(
        concepts=", ".join(top_concepts),
        node_count=DEFAULT_NODE_COUNT,
        time_ms=f"{elapsed_ms:.2f}",
    )

    # Enhance response with agentic code if safe
    if agent_proposal and safety_status == "SAFE":
        response_text += f"\n\n--- [AGENTIC PROPOSAL] ---\n{agent_proposal}"
    elif safety_status == "NEUTRALIZED":
        response_text += f"\n\n[SENTINEL ALERT] A destructive code pattern was detected and neutralized."

    raw_words = len(raw_prompt.split())
    compressed_words = len(compressed_prompt.split()) if compressed_prompt else 0
    words_saved = raw_words - compressed_words

    return {
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
