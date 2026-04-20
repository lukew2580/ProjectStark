"""
Hardwareless AI — CTranslate2 Backend
CTranslate2 fast inference for converted models.
Use this if you ran ctranslate2-converter on the original PyTorch model.
"""
import os
import asyncio
from typing import List, Dict, Any


class CTranslate2Backend:
    """
    CTranslate2 backend for models converted from PyTorch.
    Model directory should contain:
      - model.bin (or split files)
      - vocab.json / merges.txt (tokenizer)
      - config.json
    """
    
    def __init__(
        self,
        model_path: str = "models/qwen2.5-7b-ct2",
        device: str = "cpu",
        compute_type: str = "int8"
    ):
        self.model_path = model_path
        self.device = device
        self.compute_type = compute_type
        self._translator = None
        self._tokenizer = None
        self._model_loaded = False
    
    async def _ensure_loaded(self):
        if self._model_loaded:
            return
        await asyncio.to_thread(self._load_model_sync)
    
    def _load_model_sync(self):
        try:
            import ctranslate2
            from transformers import AutoTokenizer
            
            if not os.path.exists(self.model_path):
                raise FileNotFoundError(
                    f"CTranslate2 model not found at {self.model_path}.\n"
                    f"Convert a PyTorch model using: ctranslate2-converter --model <pytorch_dir> --output_dir {self.model_path}\n"
                    f"Or set QWEN_MODEL_PATH to an existing CTranslate2 model directory."
                )
            
            self._translator = ctranslate2.Translator(
                self.model_path,
                device=self.device,
                compute_type=self.compute_type
            )
            
            # Try to load tokenizer from same directory or fallback to original model name
            tokenizer_path = self.model_path
            if not os.path.exists(os.path.join(tokenizer_path, "vocab.json")):
                # Try original HuggingFace model ID as fallback
                tokenizer_path = "Qwen/Qwen2.5-7B"
            
            self._tokenizer = AutoTokenizer.from_pretrained(
                tokenizer_path,
                trust_remote_code=True
            )
            
            self._model_loaded = True
            print(f"--- [CTRANSLATE2] Model loaded from {self.model_path} on {self.device} ({self.compute_type}) ---")
            
        except ImportError as e:
            raise ImportError(
                "CTranslate2 and Transformers not installed.\n"
                "Install: pip install ctranslate2 transformers sentencepiece\n"
                "Note: CTranslate2 requires model conversion from original PyTorch."
            ) from e
    
    async def generate(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.9,
        stop: Optional[List[str]] = None
    ) -> str:
        await self._ensure_loaded()
        
        def _generate_sync():
            tokens = self._tokenizer.convert_ids_to_tokens(
                self._tokenizer.encode(prompt)
            )
            results = self._translator.generate_batch(
                [tokens],
                max_length=max_tokens,
                sampling_temperature=temperature,
                sampling_topk=1,
                sampling_topp=top_p,
                return_scores=False,
                include_prompt_in_result=False
            )
            generated_tokens = results[0].sequences_ids[0]
            return self._tokenizer.decode(generated_tokens)
        
        return await asyncio.to_thread(_generate_sync)
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "qwen2.5-7b-ct2",
        max_tokens: int = 512,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        prompt = self._format_chat_prompt(messages)
        response_text = await self.generate(prompt, max_tokens, temperature)
        
        import time
        prompt_tokens = len(self._tokenizer.encode(prompt))
        completion_tokens = len(self._tokenizer.encode(response_text))
        
        return {
            "id": f"chatcmpl-ct2-{os.urandom(4).hex()}",
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
        if self._tokenizer and hasattr(self._tokenizer, 'apply_chat_template'):
            return self._tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True
            )
        formatted = []
        for msg in messages:
            role = msg.get("role", "user").lower()
            content = msg.get("content", "")
            formatted.append(f"{role}: {content}")
        formatted.append("assistant:")
        return "\n\n".join(formatted)
    
    async def close(self):
        self._translator = None
        self._tokenizer = None
        self._model_loaded = False
