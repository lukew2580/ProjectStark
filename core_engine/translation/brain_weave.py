"""
Hardwareless AI — Brain Integration Layer
Weaves translation matrix into the hypervector brain
"""
import asyncio
import logging
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass
import numpy as np

logger = logging.getLogger("hardwareless.brain")

from core_engine.brain.vectors import generate_random_vector
from core_engine.brain.operations import bind, bundle, similarity, permute
from core_engine.translation.language_matrix import LanguageMatrix, get_language_matrix
from core_engine.translation.registry import get_registry, TranslationResult
from config.settings import DIMENSIONS


@dataclass
class BrainTranslation:
    hypervector: np.ndarray
    source_text: str
    target_text: str
    source_lang: str
    target_lang: str
    confidence: float


class BrainWeave:
    """
    Brain + Language Matrix integration.
    
    This weaves together:
    1. HDC hypervector encoding (existing encoder/decoder)
    2. Language matrix (per-language anchors)
    3. Neural translation backends (MTranServer, LibreTranslate, OPUS-MT)
    
    Flow:
    Input (any lang) → Hypervector Encode → Translate (unbind/bind) → Neural Polish → Output
    """
    
    def __init__(self):
        self.dimensions = DIMENSIONS
        self.language_matrix = get_language_matrix()
        self.registry = get_registry()
        
        self._cache: Dict[str, np.ndarray] = {}
        self._vocabulary: Dict[str, Dict[str, str]] = {}
        
    async def think(
        self,
        input_text: str,
        input_lang: str = "auto",
        target_lang: str = "en",
        polish: bool = True
    ) -> BrainTranslation:
        """
        Main entry point: process input through the full brain pipeline.
        """
        detected_lang = input_lang
        if input_lang == "auto":
            detected_lang = self._detect_language(input_text)
            
        hypervector = self.language_matrix.encode_text(input_text, detected_lang)
        
        if target_lang != detected_lang:
            hypervector = self.language_matrix.translate_hypervector(
                hypervector, detected_lang, target_lang
            )
            
        target_text = input_text
        if polish and detected_lang != target_lang:
            try:
                result = await self.registry.translate(
                    input_text, detected_lang, target_lang
                )
                target_text = result.text
            except RuntimeError as e:
                if "Circuit" in str(e) or "rate limit" in str(e):
                    logger.warning(f"Translation service unavailable: {e}")
                target_text = self._decode_approximation(hypervector, target_lang)
            except Exception as e:
                logger.error(f"Unexpected translation error: {e}")
                target_text = self._decode_approximation(hypervector, target_lang)
        else:
            target_text = self._decode_approximation(hypervector, target_lang)
            
        return BrainTranslation(
            hypervector=hypervector,
            source_text=input_text,
            target_text=target_text,
            source_lang=detected_lang,
            target_lang=target_lang,
            confidence=0.85
        )
    
    def _detect_language(self, text: str) -> str:
        """Simple language detection based on character ranges."""
        text_sample = text[:50].lower()
        
        if any('\u4e00' <= c <= '\u9fff' for c in text):
            return "zh"
        if any('\u3040' <= c <= '\u30ff' for c in text):
            return "ja"
        if any('\uac00' <= c <= '\ud7af' for c in text):
            return "ko"
        if any('\u0600' <= c <= '\u06ff' for c in text):
            return "ar"
        if any('\u0900' <= c <= '\u097f' for c in text):
            return "hi"
        if any('\u0e00' <= c <= '\u0e7f' for c in text):
            return "th"
            
        return "en"
    
    def _decode_approximation(self, hypervector: np.ndarray, target_lang: str) -> str:
        """
        Approximate decode - returns a placeholder when exact decode unavailable.
        Uses language anchor to generate a representative string.
        """
        anchor = self.language_matrix.get_language_anchor(target_lang)
        if anchor is not None:
            sim = similarity(hypervector, anchor, self.dimensions)
            return f"[{target_lang.upper()}] HDC vector, similarity: {sim:.2f}"
        return f"[UNKNOWN] HDC vector"
    
    def encode_concept(self, concept: str, lang: str = "en") -> np.ndarray:
        """Encode a concept into a hypervector."""
        return self.language_matrix.encode_text(concept, lang)
    
    def bind_concepts(self, vec_a: np.ndarray, vec_b: np.ndarray) -> np.ndarray:
        """Bind two hypervectors to create an association."""
        return bind(vec_a, vec_b)
    
    def bundle_concepts(self, vectors: List[np.ndarray]) -> np.ndarray:
        """Bundle multiple hypervectors into one."""
        return bundle(vectors, self.dimensions)
    
    def find_similar(
        self,
        query_vector: np.ndarray,
        concept_vectors: Dict[str, np.ndarray],
        top_k: int = 5
    ) -> List[Tuple[str, float]]:
        """Find most similar concepts to a query vector."""
        scores = []
        for name, vec in concept_vectors.items():
            score = similarity(query_vector, vec, self.dimensions)
            scores.append((name, score))
            
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]
    
    def activate_language(self, lang_code: str):
        """Activate a language in the matrix for faster lookups."""
        anchor = self.language_matrix.get_language_anchor(lang_code)
        return anchor is not None
    
    def get_supported_languages(self) -> List[str]:
        return self.language_matrix.get_supported_languages()
    
    def add_concept_to_brain(
        self,
        concept: str,
        language: str,
        vector: Optional[np.ndarray] = None
    ):
        """Add a concept to the brain's working memory."""
        if vector is None:
            vector = self.encode_concept(concept, language)
            
        key = f"{language}:{concept.lower()}"
        self._cache[key] = vector
        
    def recall(self, concept: str, language: str = "en") -> Optional[np.ndarray]:
        """Recall a concept from the brain's working memory."""
        key = f"{language}:{concept.lower()}"
        return self._cache.get(key)


_global_weave: Optional[BrainWeave] = None

def get_weave() -> BrainWeave:
    global _global_weave
    if _global_weave is None:
        _global_weave = BrainWeave()
    return _global_weave