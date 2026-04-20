"""
Hardwareless AI — Ollama Backend
External Ollama service integration (OpenAI-compatible API).
"""
import os
import asyncio
from typing import List, Dict, Any
import aiohttp


class OllamaBackend:
    """
    Ollama service backend for running models via `ollama serve`.
    Communicates via Ollama's HTTP API (which is OpenAI-compatible).
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model_name: str = "qwen2.5:7b"
    ):
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        self._session: Optional[aiohttp.ClientSession] = None
        self._ready = False
    
    async def _ensure_session(self):
        if self._session is None:
            self._session = aiohttp.ClientSession()
    
    async def _ensure_loaded(self):
        """Check Ollama is running and model is available."""
        await self._ensure_session()
        try:
            # Check Ollama health
            async with self._session.get(f"{self.base_url}/api/tags") as resp:
                if resp.status != 200:
                    raise RuntimeError(f"Ollama not reachable at {self.base_url}")
                data = await resp.json()
                models = [m["name"] for m in data.get("models", [])]
                if self.model_name not in models:
                    raise RuntimeError(
                        f"Model '{self.model_name}' not found in Ollama. "
                        f"Run: ollama pull {self.model_name}"
                    )
            self._ready = True
            print(f"--- [OLLAMA] Connected to {self.base_url}, model {self.model_name} ready ---")
        except aiohttp.ClientError as e:
            raise RuntimeError(f"Cannot connect to Ollama at {self.base_url}: {e}")
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "ollama-qwen2.5",
        max_tokens: int = 512,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """
        OpenAI-style chat completion via Ollama API.
        """
        await self._ensure_loaded()
        
        # Ollama uses non-streaming generate endpoint
        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature,
            }
        }
        
        async with self._session.post(
            f"{self.base_url}/v1/chat/completions",
            json=payload
        ) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                raise RuntimeError(f"Ollama API error {resp.status}: {error_text}")
            
            result = await resp.json()
            
            # Transform to OpenAI format
            return {
                "id": result.get("id", f"ollama-{os.urandom(4).hex()}"),
                "object": "chat.completion",
                "created": result.get("created", int(__import__('time').time())),
                "model": model,
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": result["choices"][0]["message"]["role"],
                        "content": result["choices"][0]["message"]["content"]
                    },
                    "finish_reason": result["choices"][0].get("finish_reason", "stop")
                }],
                "usage": result.get("usage", {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0
                })
            }
    
    async def close(self):
        """Close HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None
        self._ready = False
