"""
Hardwareless AI — Language Matrix
HDC-based multilingual hypervector system
"""
import json
import hashlib
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from core_engine.brain.vectors import generate_random_vector
from core_engine.brain.operations import bind, bundle, similarity
from config.settings import DIMENSIONS


LANGUAGE_CODES = {
    "en": "ENGLISH", "zh": "CHINESE", "es": "SPANISH", "hi": "HINDI",
    "ar": "ARABIC", "fr": "FRENCH", "bn": "BENGALI", "pt": "PORTUGUESE",
    "ru": "RUSSIAN", "ur": "URDU", "ja": "JAPANESE", "de": "GERMAN",
    "ko": "KOREAN", "it": "ITALIAN", "tr": "TURKISH", "vi": "VIETNAMESE",
    "ta": "TAMIL", "sw": "SWAHILI", "th": "THAI", "pl": "POLISH"
}

@dataclass
class LanguageVector:
    code: str
    name: str
    anchor_vector: np.ndarray

class LanguageMatrix:
    """
    HDC Language Matrix for multilingual operations.
    
    Architecture:
    - Each language has a unique anchor hypervector (language signature)
    - Each word maps to a language-specific binding
    - Translation = unbind source language, bind target language
    """
    
    def __init__(self, dimensions: int = DIMENSIONS):
        self.dimensions = dimensions
        self.language_anchors: Dict[str, LanguageVector] = {}
        self.word_cache: Dict[Tuple[str, str], np.ndarray] = {}
        self._initialize_languages()
        
    def _initialize_languages(self):
        """Generate anchor vectors for each supported language."""
        for code, name in LANGUAGE_CODES.items():
            seed = self._hash_to_seed(f"LANG_{name}")
            anchor = generate_random_vector(self.dimensions, seed=seed)
            self.language_anchors[code] = LanguageVector(
                code=code,
                name=name,
                anchor_vector=anchor
            )
            
    def _hash_to_seed(self, text: str) -> int:
        """Convert text to deterministic seed."""
        h = hashlib.sha256(text.encode()).digest()
        return int.from_bytes(h[:4], 'big')
    
    def get_language_anchor(self, lang_code: str) -> Optional[np.ndarray]:
        """Get the anchor vector for a language."""
        if lang_code in self.language_anchors:
            return self.language_anchors[lang_code].anchor_vector
        if lang_code.lower() in self.language_anchors:
            return self.language_anchors[lang_code.lower()].anchor_vector
        return None
    
    def get_word_vector(self, word: str, lang_code: str) -> np.ndarray:
        """Get the hypervector for a word in a specific language."""
        cache_key = (word.lower(), lang_code)
        if cache_key in self.word_cache:
            return self.word_cache[cache_key]
            
        lang_anchor = self.get_language_anchor(lang_code)
        if lang_anchor is None:
            raise ValueError(f"Unknown language: {lang_code}")
            
        word_seed = self._hash_to_seed(f"{lang_code}_{word.lower()}")
        word_vec = generate_random_vector(self.dimensions, seed=word_seed)
        
        bound = bind(lang_anchor, word_vec)
        self.word_cache[cache_key] = bound
        return bound
    
    def encode_text(self, text: str, lang_code: str) -> np.ndarray:
        """Encode a full text into a single hypervector."""
        words = text.lower().strip().split()
        if not words:
            return np.zeros(self.dimensions, dtype=np.int8)
            
        word_vectors = [self.get_word_vector(w, lang_code) for w in words]
        return bundle(word_vectors, self.dimensions)
    
    def translate_hypervector(self, hypervector: np.ndarray, 
                             source_lang: str, target_lang: str) -> np.ndarray:
        """Translate by unbinding source language, binding target."""
        source_anchor = self.get_language_anchor(source_lang)
        target_anchor = self.get_language_anchor(target_lang)
        
        if source_anchor is None or target_anchor is None:
            raise ValueError(f"Unknown language: {source_lang} or {target_lang}")
            
        unbind_source = bind(hypervector, source_anchor)
        return bind(unbind_source, target_anchor)
    
    def similarity(self, vec_a: np.ndarray, vec_b: np.ndarray) -> float:
        return similarity(vec_a, vec_b, self.dimensions)
    
    def find_closest_language(self, hypervector: np.ndarray) -> str:
        """Find which language a hypervector is closest to."""
        best_lang = "en"
        best_score = -1.0
        
        for code, lang_vec in self.language_anchors.items():
            score = similarity(hypervector, lang_vec.anchor_vector, self.dimensions)
            if score > best_score:
                best_score = score
                best_lang = code
                
        return best_lang
    
    def add_language(self, code: str, name: str):
        """Dynamically add a new language to the matrix."""
        if code in self.language_anchors:
            return
            
        seed = self._hash_to_seed(f"LANG_{name}")
        anchor = generate_random_vector(self.dimensions, seed=seed)
        self.language_anchors[code] = LanguageVector(
            code=code,
            name=name,
            anchor_vector=anchor
        )
        
    def get_supported_languages(self) -> List[str]:
        return list(self.language_anchors.keys())
    
    def dump_anchors(self) -> Dict[str, List[int]]:
        """Export anchors for serialization (not actual vectors, just metadata)."""
        return {
            code: lang_vec.name 
            for code, lang_vec in self.language_anchors.items()
        }


_global_matrix: Optional[LanguageMatrix] = None

def get_language_matrix() -> LanguageMatrix:
    global _global_matrix
    if _global_matrix is None:
        _global_matrix = LanguageMatrix()
    return _global_matrix