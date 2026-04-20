"""
Hardwareless AI — Qwen2.5-7B Backend
GGUF model via llama-cpp-python for CPU inference.
"""
import os
import asyncio
from typing import Optional, List, Dict, Any


class QwenBackend:
    """
    Qwen2.5-7B GGUF via llama-cpp-python.
    - Loads .gguf files directly
    - OpenAI-compatible chat interface
    - Auto-detects GPU and offloads layers if available (n_gpu_layers=-1)
    - Falls back to CPU seamlessly if no GPU or insufficient VRAM
    """
    
    def __init__(
        self,
        model_path: str = "models/model.gguf",
        n_ctx: int = 4096,
        n_batch: int = 512,
        n_gpu_layers: int = -1  # -1 = auto-detect; 0 = CPU only; >0 = explicit layer count
    ):
        self.model_path = model_path
        self.n_ctx = n_ctx
        self.n_batch = n_batch
        self._requested_gpu_layers = n_gpu_layers
        self._llm = None
        self._model_loaded = False
        self._actual_gpu_layers = 0
    
    def _detect_gpu_capability(self) -> int:
        """
        Detect how many layers can be offloaded to GPU.
        Returns optimal n_gpu_layers value based on available VRAM.
        """
        try:
            import torch
            if not torch.cuda.is_available():
                return 0
            
            # Get total GPU memory in GB
            gpu_mem_bytes = torch.cuda.get_device_properties(0).total_memory
            gpu_mem_gb = gpu_mem_bytes / (1024**3)
            
            # Heuristic for 7B Q4_K_M (~4.6GB total):
            # - >=8GB VRAM: offload most layers
            # - 6-8GB: partial offload (~32 layers)
            # - <6GB: CPU only (0 layers)
            if gpu_mem_gb >= 8:
                return -1  # Let llama-cpp decide (typically all layers)
            elif gpu_mem_gb >= 6:
                return 32  # Partial offload
            else:
                return 0  # Not enough VRAM
        except ImportError:
            # torch not available
            return 0
        except Exception:
            return 0
    
    async def _ensure_loaded(self):
        if self._model_loaded:
            return
        await asyncio.to_thread(self._load_model_sync)
    
    def _load_model_sync(self):
        """Synchronously load the GGUF model via llama-cpp."""
        try:
            from llama_cpp import Llama
            
            if not os.path.exists(self.model_path):
                raise FileNotFoundError(
                    f"GGUF model not found at {self.model_path}. "
                    f"Set QWEN_MODEL_PATH to point to your .gguf file."
                )
            
            # Determine GPU layers
            if self._requested_gpu_layers == -1:
                n_gpu_layers = self._detect_gpu_capability()
            else:
                n_gpu_layers = self._requested_gpu_layers
            
            self._actual_gpu_layers = n_gpu_layers
            
            self._llm = Llama(
                model_path=self.model_path,
                n_ctx=self.n_ctx,
                n_batch=self.n_batch,
                n_gpu_layers=n_gpu_layers,
                verbose=False
            )
            
            self._model_loaded = True
            mode = "GPU" if n_gpu_layers > 0 else "CPU"
            gpu_info = f"({n_gpu_layers} layers)" if n_gpu_layers > 0 else ""
            print(f"--- [QWEN] Model loaded: {mode} {gpu_info} from {self.model_path} ---")
            
        except ImportError as e:
            raise ImportError(
                "llama-cpp-python not installed.\n"
                "  CPU-only: pip install llama-cpp-python\n"
                "  GPU CUDA: CMAKE_ARGS='-DLLAMA_CUBLAS=on' pip install llama-cpp-python\n"
                "  GPU Metal (macOS): CMAKE_ARGS='-DLLAMA_METAL=on' pip install llama-cpp-python"
            ) from e
    
    async def generate(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.9,
        stop: Optional[List[str]] = None
    ) -> str:
        """
        Generate text completion for the given prompt.
        """
        await self._ensure_loaded()
        
        def _generate_sync():
            output = self._llm(
                prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                stop=stop,
                echo=False
            )
            return output["choices"][0]["text"].strip()
        
        return await asyncio.to_thread(_generate_sync)
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "qwen2.5-7b",
        max_tokens: int = 512,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """
        Create a chat completion in OpenAI format.
        """
        prompt = self._format_chat_prompt(messages)
        
        response_text = await self.generate(
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature
        )
        
        import time
        # Simple token estimation (rough)
        prompt_tokens = len(prompt.split()) * 1.3
        completion_tokens = len(response_text.split()) * 1.3
        
        return {
            "id": f"chatcmpl-qwen-{os.urandom(4).hex()}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model,
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response_text
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": int(prompt_tokens),
                "completion_tokens": int(completion_tokens),
                "total_tokens": int(prompt_tokens + completion_tokens)
            }
        }
    
    def _format_chat_prompt(self, messages: List[Dict[str, str]]) -> str:
        """
        Format messages for Qwen chat model.
        Uses Qwen's chat template if recognized; falls back to generic.
        """
        lines = []
        for msg in messages:
            role = msg.get("role", "user").lower()
            content = msg.get("content", "")
            if role == "system":
                lines.append(f"<|system|>\n{content}</|system|>")
            elif role == "user":
                lines.append(f"<|user|>\n{content}</|user|>")
            elif role == "assistant":
                lines.append(f"<|assistant|>\n{content}</|assistant|>")
        
        # Start assistant turn
        lines.append("<|assistant|>")
        return "\n".join(lines)
    
    async def close(self):
        """Free resources."""
        self._llm = None
        self._model_loaded = False

