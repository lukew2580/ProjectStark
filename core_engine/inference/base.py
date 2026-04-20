"""
Common backend interface for all LLM inference backends.
All backends must implement .chat_completion(messages, model, **kwargs) -> dict.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any


class BaseBackend(ABC):
    """Abstract base class for inference backends."""
    
    @abstractmethod
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str,
        max_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.9
    ) -> Dict[str, Any]:
        """
        OpenAI-style chat completion.
        Returns dict with keys: id, object, created, model, choices, usage
        """
        pass
    
    @abstractmethod
    async def initialize(self) -> None:
        """Load model, warm caches."""
        pass
    
    @abstractmethod
    async def shutdown(self) -> None:
        """Free resources."""
        pass
    
    @property
    @abstractmethod
    def is_ready(self) -> bool:
        """True if model loaded and ready."""
        pass
