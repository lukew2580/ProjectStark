"""
Hardwareless AI — Sentiment-Aware Translation
Translates while preserving sentiment and tone
"""
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum


class Sentiment(Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    FORMAL = "formal"
    INFORMAL = "informal"
    URGENT = "urgent"
    CALM = "calm"


@dataclass
class SentimentAnalysis:
    sentiment: Sentiment
    confidence: float
    indicators: List[str]


class SentimentTranslator:
    """
    Translates text while maintaining sentiment/tone.
    - Detects sentiment before translation
    - Adjusts output to preserve tone
    - Handles formal/informal appropriately
    """
    
    def __init__(self):
        self._sentiment_words = self._init_sentiment_lexicon()
        self._formality_markers = self._init_formality()
    
    def _init_sentiment_lexicon(self) -> Dict[str, Dict[str, List[str]]]:
        """Initialize sentiment indicators."""
        return {
            "positive": {
                "en": ["good", "great", "excellent", "amazing", "wonderful", "love", "happy", "fantastic"],
                "es": ["bueno", "excelente", "increíble", "maravilloso", "amor", "feliz"],
                "fr": ["bon", "excellent", "incroyable", "merveilleux", "amour", "heureux"]
            },
            "negative": {
                "en": ["bad", "terrible", "awful", "hate", "sad", "worst", "horrible", "angry"],
                "es": ["malo", "terrible", "espantoso", "odio", "triste", "peor"],
                "fr": ["mauvais", "terrible", "affreux", "colère", "triste"]
            }
        }
    
    def _init_formality(self) -> Dict[str, Dict[str, str]]:
        """Initialize formality markers."""
        return {
            "formal": {
                "en": {"you": "you", "hello": "greetings", "thanks": "thank you"},
                "es": {"tu": "usted", "hola": "buenos días", "gracias": "muchas gracias"}
            },
            "informal": {
                "en": {"you": "ya", "hello": "hey", "thanks": "thx"},
                "es": {"tu": "tú", "hola": "hola", "gracias": "gracias"}
            }
        }
    
    async def analyze_sentiment(self, text: str, lang: str = "en") -> SentimentAnalysis:
        """Analyze sentiment of text."""
        text_lower = text.lower()
        
        # Check positive indicators
        positive_count = 0
        positive_words = self._sentiment_words.get("positive", {}).get(lang, [])
        for word in positive_words:
            if word in text_lower:
                positive_count += 1
        
        # Check negative indicators
        negative_count = 0
        negative_words = self._sentiment_words.get("negative", {}).get(lang, [])
        for word in negative_words:
            if word in text_lower:
                negative_count += 1
        
        # Determine sentiment
        if positive_count > negative_count:
            sentiment = Sentiment.POSITIVE
            confidence = positive_count / max(positive_count + negative_count, 1)
        elif negative_count > positive_count:
            sentiment = Sentiment.NEGATIVE
            confidence = negative_count / max(positive_count + negative_count, 1)
        else:
            sentiment = Sentiment.NEUTRAL
            confidence = 0.5
        
        indicators = []
        if positive_count > 0:
            indicators.append(f"+{positive_count} positive words")
        if negative_count > 0:
            indicators.append(f"-{negative_count} negative words")
        
        return SentimentAnalysis(
            sentiment=sentiment,
            confidence=confidence,
            indicators=indicators
        )
    
    async def translate_with_tone(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        preserve_sentiment: bool = True,
        formality: str = "neutral"
    ) -> Dict:
        """Translate preserving sentiment and tone."""
        # Analyze sentiment
        sentiment = await self.analyze_sentiment(text, source_lang)
        
        # Would integrate with actual translation service
        # For now, return sentiment info
        return {
            "text": text,
            "source_lang": source_lang,
            "target_lang": target_lang,
            "detected_sentiment": sentiment.sentiment.value,
            "sentiment_confidence": sentiment.confidence,
            "indicators": sentiment.indicators,
            "formality": formality
        }


_global_sentiment: Optional[SentimentTranslator] = None


def get_sentiment_translator() -> SentimentTranslator:
    global _global_sentiment
    if _global_sentiment is None:
        _global_sentiment = SentimentTranslator()
    return _global_sentiment