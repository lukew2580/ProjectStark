"""
Hardwareless AI — Language Detection Service
Detects language from text using HDC hypervectors
"""
import hashlib
from typing import Dict, List, Optional, Tuple

from core_engine.brain.vectors import generate_random_vector
from core_engine.brain.operations import similarity
from core_engine.translation.language_matrix import LANGUAGE_CODES
from config.settings import DIMENSIONS


class LanguageDetector:
    """
    Detects language from text using HDC similarity.
    
    Uses character n-grams as language fingerprints.
    """
    
    def __init__(self, dimensions: int = DIMENSIONS):
        self.dimensions = dimensions
        self._ngram_fingerprints = self._init_ngrams()
    
    def _init_ngrams(self) -> Dict[str, Dict[str, float]]:
        """Initialize language fingerprints (n-gram distributions)."""
        # Common character n-grams for each language
        fingerprints = {
            "en": {
                " the ": 0.05, "ing ": 0.03, " and": 0.03, " of ": 0.03,
                " to ": 0.03, " an ": 0.02, " in ": 0.02, " is ": 0.02,
                " to": 0.02, "th": 0.02, "he": 0.02, " t": 0.02
            },
            "es": {
                " el ": 0.03, " de ": 0.03, " que ": 0.03, " la ": 0.03,
                " en ": 0.02, " os ": 0.02, " que": 0.02, " es ": 0.02,
                " a ": 0.02, " un ": 0.02, " do": 0.02, " de": 0.02
            },
            "fr": {
                " le ": 0.03, " de ": 0.03, " et ": 0.03, " la ": 0.03,
                " ue ": 0.02, " es ": 0.02, " nt ": 0.02, " on ": 0.02,
                " un ": 0.02, " ent": 0.02, " qu": 0.02
            },
            "de": {
                " er ": 0.03, " ch ": 0.03, " de ": 0.03, " die ": 0.03,
                " und": 0.02, " en ": 0.02, " ich": 0.02, " das": 0.02,
                " ein": 0.02, " ten": 0.02
            },
            "zh": {
                "的": 0.08, "是": 0.04, "了": 0.04, "在": 0.03,
                "我": 0.03, "有": 0.02, "和": 0.02, "人": 0.02,
                "这": 0.02, "个": 0.02, "上": 0.02, "也": 0.02
            },
            "ja": {
                "の": 0.06, "に": 0.04, "は": 0.04, "を": 0.03,
                "た": 0.02, "い": 0.02, "し": 0.02, "る": 0.02,
                "と": 0.02, "が": 0.02, "な": 0.02, "て": 0.02
            },
            "ru": {
                " и ": 0.04, " в ": 0.03, " не ": 0.03, " на ": 0.03,
                "по": 0.02, "то": 0.02, "ов": 0.02, "ка": 0.02,
                "ст": 0.02, "ет": 0.02
            },
            "ar": {
                " ال": 0.05, " في ": 0.03, " من ": 0.03, " على ": 0.03,
                "لا": 0.02, "ما": 0.02, "ني": 0.02, "ون": 0.02,
                "ال": 0.02
            }
        }
        return fingerprints
    
    async def detect(self, text: str, top_n: int = 3) -> List[Dict]:
        """Detect language from text."""
        if not text:
            return [{"language": "unknown", "confidence": 0.0}]
        
        text_lower = text.lower()
        scores = {}
        
        # Score against each language fingerprint
        for lang, fingerprint in self._ngram_fingerprints.items():
            score = 0.0
            total_grams = 0
            
            for ngram, weight in fingerprint.items():
                count = text_lower.count(ngram)
                score += count * weight
                total_grams += count
            
            if total_grams > 0:
                scores[lang] = score / min(total_grams, 10)
        
        if not scores:
            return [{"language": "unknown", "confidence": 0.0}]
        
        # Sort by score
        sorted_langs = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        results = []
        for lang, score in sorted_langs[:top_n]:
            lang_name = LANGUAGE_CODES.get(lang, lang.upper())
            results.append({
                "language": lang,
                "name": lang_name,
                "confidence": min(score * 10, 1.0)
            })
        
        return results
    
    async def detect_code(self, text: str) -> str:
        """Detect language code."""
        results = await self.detect(text, top_n=1)
        return results[0]["language"] if results else "en"


_global_detector: Optional[LanguageDetector] = None


def get_language_detector() -> LanguageDetector:
    global _global_detector
    if _global_detector is None:
        _global_detector = LanguageDetector()
    return _global_detector