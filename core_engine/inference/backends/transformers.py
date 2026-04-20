"""
Hardwareless AI — Transformers Backend
HuggingFace Transformers direct inference for PyTorch models.
Uses pipeline or model.generate() for text generation.
"""
import os
import asyncio
from typing import List, Dict, Any, Optional
from pathlib import Path


class TransformersBackend:
    """
    HuggingFace Transformers backend.
    Loads models from local directory or HuggingFace Hub.
    Supports any PyTorch model (including original Qwen2.5-7B).
    Works on both GPU and CPU — auto-detects best device.
    """
    
    def __init__(
        self,
        model_id_or_path: str = "Qwen/Qwen2.5-7B",
        device: str = "auto",  # "cpu", "cuda", "mps", "auto"
        torch_dtype: str = "auto",  # "auto", "float16", "bfloat16", "float32"
        load_in_4bit: bool = False,
        load_in_8bit: bool = False,
        device_map: Optional[str] = None  # "auto", None = default
    ):
        self.model_id_or_path = model_id_or_path
        self._device_param = device
        self.torch_dtype = torch_dtype
        self.load_in_4bit = load_in_4bit
        self.load_in_8bit = load_in_8bit
        self.device_map = device_map
        self._pipeline = None
        self._model = None
        self._tokenizer = None
        self._model_loaded = False
        self._resolved_device = None
    
    def _resolve_device(self):
        """Resolve device based on availability and config."""
        if self._device_param == "auto":
            try:
                import torch
                if torch.cuda.is_available():
                    return "cuda"
                if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                    return "mps"
            except ImportError:
                pass
            return "cpu"
        return self._device_param
    
    async def _ensure_loaded(self):
        if self._model_loaded:
            return
        await asyncio.to_thread(self._load_model_sync)
    
    def _load_model_sync(self):
        """Load model and tokenizer with transformers."""
        try:
            from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
            import torch
            
            # Resolve device
            device = self._resolve_device()
            self._resolved_device = device
            print(f"--- [TRANSFORMERS] Device resolved: {device} ---")
            
            # Determine dtype based on device and config
            if self.torch_dtype == "auto":
                if device in ("cuda", "mps"):
                    dtype = torch.float16
                else:
                    dtype = torch.float32
            elif self.torch_dtype == "float16":
                dtype = torch.float16
            elif self.torch_dtype == "bfloat16":
                dtype = torch.bfloat16
            else:
                dtype = torch.float32
            
            # Quantization options (requires bitsandbytes for 4bit/8bit)
            quant_kwargs = {}
            if self.load_in_4bit:
                try:
                    import bitsandbytes as bnb
                    quant_kwargs["load_in_4bit"] = True
                except ImportError:
                    print("WARNING: bitsandbytes not installed; 4-bit loading unavailable")
            elif self.load_in_8bit:
                try:
                    import bitsandbytes as bnb
                    quant_kwargs["load_in_8bit"] = True
                except ImportError:
                    print("WARNING: bitsandbytes not installed; 8-bit loading unavailable")
            
            # Load tokenizer
            self._tokenizer = AutoTokenizer.from_pretrained(
                self.model_id_or_path,
                trust_remote_code=True
            )
            
            # Determine device_map
            if self.device_map is not None:
                device_map = self.device_map
            elif device == "cpu":
                device_map = None  # CPU: load on CPU, no device map needed
            else:
                device_map = "auto"  # Let transformers distribute across GPU(s)
            
            # Load model
            self._model = AutoModelForCausalLM.from_pretrained(
                self.model_id_or_path,
                torch_dtype=dtype,
                device_map=device_map,
                trust_remote_code=True,
                **quant_kwargs
            )
            
            # Ensure model is on correct device if no device_map used
            if device_map is None:
                if device == "cuda":
                    self._model = self._model.cuda()
                elif device == "mps":
                    self._model = self._model.to("mps")
                else:
                    self._model = self._model.cpu()
            
            # Build pipeline (optional convenience)
            pipeline_device = 0 if device in ("cuda", "mps") else -1
            self._pipeline = pipeline(
                "text-generation",
                model=self._model,
                tokenizer=self._tokenizer,
                device=pipeline_device
            )
            
            self._model_loaded = True
            print(f"--- [TRANSFORMERS] Model loaded: {self.model_id_or_path} on {device} ---")
            
        except ImportError as e:
            raise ImportError(
                "Transformers and torch not installed. Install with:\n"
                "pip install transformers torch sentencepiece\n"
                "Optional (quantization): pip install bitsandbytes accelerate"
            ) from e
    
    async def generate(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.9
    ) -> str:
        await self._ensure_loaded()
        
        def _generate_sync():
            # Use pipeline if available, otherwise manual generate
            if self._pipeline:
                outputs = self._pipeline(
                    prompt,
                    max_new_tokens=max_tokens,
                    temperature=temperature,
                    top_p=top_p,
                    do_sample=True
                )
                return outputs[0]["generated_text"][len(prompt):]
            else:
                # Manual generation
                inputs = self._tokenizer(prompt, return_tensors="pt").to(self._model.device)
                with torch.no_grad():
                    outputs = self._model.generate(
                        **inputs,
                        max_new_tokens=max_tokens,
                        temperature=temperature,
                        top_p=top_p,
                        do_sample=True
                    )
                return self._tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
        
        return await asyncio.to_thread(_generate_sync)
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "transformers-qwen",
        max_tokens: int = 512,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        prompt = self._format_chat_prompt(messages)
        response_text = await self.generate(prompt, max_tokens, temperature)
        
        import time
        prompt_tokens = len(self._tokenizer.encode(prompt))
        completion_tokens = len(self._tokenizer.encode(response_text))
        
        return {
            "id": f"chatcmpl-tf-{os.urandom(4).hex()}",
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
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens
            }
        }
    
    def _format_chat_prompt(self, messages: List[Dict[str, str]]) -> str:
        """Format chat messages for Qwen-style models using tokenizer chat template."""
        if self._tokenizer and hasattr(self._tokenizer, 'apply_chat_template'):
            return self._tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True
            )
        # Simple fallback
        formatted = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            formatted.append(f"{role.capitalize()}: {content}")
        formatted.append("Assistant:")
        return "\n\n".join(formatted)
    
    async def close(self):
        """Free GPU memory."""
        import gc
        import torch
        if self._model is not None:
            del self._model
        if self._pipeline is not None:
            del self._pipeline
        self._model = None
        self._pipeline = None
        self._tokenizer = None
        self._model_loaded = False
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
