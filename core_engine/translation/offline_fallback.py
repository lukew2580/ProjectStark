"""
Hardwareless AI — Offline Fallback Translation
Uses HDC language matrix when online services unavailable
"""
import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass

from core_engine.translation.language_matrix import LANGUAGE_CODES, get_language_matrix
from core_engine.brain.operations import bind, similarity
from config.settings import DIMENSIONS


@dataclass
class FallbackTranslationResult:
    text: str
    source_lang: str
    target_lang: str
    backend: str = "hdc_fallback"
    confidence: float = 0.5


class OfflineFallback:
    """
    Offline fallback using HDC language matrix.
    Provides translations when online services fail.
    """
    
    def __init__(self, dimensions: int = DIMENSIONS):
        self.dimensions = dimensions
        self._matrix = None
        self._lexicon: Dict[str, Dict[str, str]] = {}
        self._load_minimal_lexicon()
    
    def _load_minimal_lexicon(self):
        """Load minimal lexicon for offline use."""
        # Core phrases in all supported languages
        core_phrases = {
            "hello": {
                "en": "Hello", "es": "Hola", "fr": "Bonjour", "de": "Hallo",
                "zh": "你好", "ja": "こんにちは", "ko": "안녕하세요", "ru": "Привет",
                "ar": "مرحبا", "hi": "नमस्ते", "pt": "Olá", "it": "Ciao",
                "tr": "Merhaba", "vi": "Xin chào", "th": "สวัสดี", "pl": "Cześć",
                "id": "Halo", "nl": "Hallo", "sv": "Hej", "da": "Hej",
                "no": "Hei", "fi": "Hei", "el": "Γεια σου", "he": "שלום",
                "cs": "Ahoj", "ro": "Bună"
            },
            "goodbye": {
                "en": "Goodbye", "es": "Adiós", "fr": "Au revoir", "de": "Auf Wiedersehen",
                "zh": "再见", "ja": "さようなら", "ko": "안녕히 가세요", "ru": "До свидания",
                "ar": "مع السلامة", "hi": "अलविदा", "pt": "Adeus", "it": "Arrivederci",
                "tr": "Hoşçakal", "vi": "Tạm biệt", "th": "ลาก่อน", "pl": "Do widzenia",
                "id": "Selamat tinggal", "nl": "Tot ziens", "sv": "Adjö", "da": "Farvel",
                "no": "Ha det", "fi": "Näkemiin", "el": "Αντίο", "he": "להתראות",
                "cs": "Nashle", "ro": "La revedere"
            },
            "thank_you": {
                "en": "Thank you", "es": "Gracias", "fr": "Merci", "de": "Danke",
                "zh": "谢谢", "ja": "ありがとう", "ko": "감사합니다", "ru": "Спасибо",
                "ar": "شكرا", "hi": "धन्यवाद", "pt": "Obrigado", "it": "Grazie",
                "tr": "Teşekkür ederim", "vi": "Cảm ơn", "th": "ขอบคุณ", "pl": "Dziękuję",
                "id": "Terima kasih", "nl": "Bedankt", "sv": "Tack", "da": "Tak",
                "no": "Takk", "fi": "Kiitos", "el": "Ευχαριστώ", "he": "תודה",
                "cs": "Děkuji", "ro": "Mulțumesc"
            },
            "yes": {
                "en": "Yes", "es": "Sí", "fr": "Oui", "de": "Ja",
                "zh": "是", "ja": "はい", "ko": "네", "ru": "Да",
                "ar": "نعم", "hi": "हाँ", "pt": "Sim", "it": "Sì",
                "tr": "Evet", "vi": "Vâng", "th": "ใช่", "pl": "Tak",
                "id": "Ya", "nl": "Ja", "sv": "Ja", "da": "Ja",
                "no": "Ja", "fi": "Kyllä", "el": "Ναι", "he": "כן",
                "cs": "Ano", "ro": "Da"
            },
            "no": {
                "en": "No", "es": "No", "fr": "Non", "de": "Nein",
                "zh": "不", "ja": "いいえ", "ko": "아니요", "ru": "Нет",
                "ar": "لا", "hi": "नहीं", "pt": "Não", "it": "No",
                "tr": "Hayır", "vi": "Không", "th": "ไม่", "pl": "Nie",
                "id": "Tidak", "nl": "Nee", "sv": "Nej", "da": "Nej",
                "no": "Nei", "fi": "Ei", "el": "Όχι", "he": "לא",
                "cs": "Ne", "ro": "Nu"
            },
            "please": {
                "en": "Please", "es": "Por favor", "fr": "S'il vous plaît", "de": "Bitte",
                "zh": "请", "ja": "お願いします", "ko": "부탁합니다", "ru": "Пожалуйста",
                "ar": "من فضلك", "hi": "कृपया", "pt": "Por favor", "it": "Per favore",
                "tr": "Lütfen", "vi": "Xin vui lòng", "th": "กรุณา", "pl": "Proszę",
                "id": "Tolong", "nl": "Alstublieft", "sv": "Varsågod", "da": "Venligst",
                "no": "Vennligst", "fi": "Ole hyvä", "el": "Παρακαλώ", "he": "בבקשה",
                "cs": "Prosím", "ro": "Vă rog"
            },
            "sorry": {
                "en": "Sorry", "es": "Lo siento", "fr": "Désolé", "de": "Entschuldigung",
                "zh": "对不起", "ja": "ごめんなさい", "ko": "죄송합니다", "ru": "Извините",
                "ar": "أنا آسف", "hi": "माफ करना", "pt": "Desculpe", "it": "Mi dispiace",
                "tr": "Özür dilerim", "vi": "Xin lỗi", "th": "ขอโทษ", "pol": "Przepraszam",
                "id": "Maaf", "nl": "Sorry", "sv": "Förlåt", "da": "Undskyld",
                "no": "Beklager", "fi": "Olen pahoillani", "el": "Συγγνώμη", "he": "סליחה",
                "cs": "Omlouvám se", "ro": "Scuze"
            },
            "help": {
                "en": "Help", "es": "Ayuda", "fr": "Aide", "de": "Hilfe",
                "zh": "帮助", "ja": "助けて", "ko": "도움", "ru": "Помощь",
                "ar": "مساعدة", "hi": "मदद", "pt": "Ajuda", "it": "Aiuto",
                "tr": "Yardım", "vi": "Giúp đỡ", "th": "ช่วยด้วย", "pl": "Pomoc",
                "id": "Bantuan", "nl": "Hulp", "sv": "Hjälp", "da": "Hjælp",
                "no": "Hjelp", "fi": "Apua", "el": "Βοήθεια", "he": "עזרה",
                "cs": "Pomoc", "ro": "Ajutor"
            }
        }
        
        self._lexicon = core_phrases
    
    async def translate(
        self,
        text: str,
        source_lang: str = "auto",
        target_lang: str = "en"
    ) -> FallbackTranslationResult:
        """Translate using offline lexicon."""
        text_lower = text.lower().strip()
        
        # Direct lookup in lexicon
        for phrase_key, translations in self._lexicon.items():
            if text_lower in translations:
                translated = translations.get(target_lang, text)
                return FallbackTranslationResult(
                    text=translated,
                    source_lang=source_lang,
                    target_lang=target_lang,
                    backend="hdc_fallback",
                    confidence=0.7
                )
            
            # Check if input matches any known phrase
            for src_code, src_text in translations.items():
                if src_text.lower() == text_lower:
                    translated = translations.get(target_lang, text)
                    return FallbackTranslationResult(
                        text=translated,
                        source_lang=source_lang,
                        target_lang=target_lang,
                        backend="hdc_fallback",
                        confidence=0.6
                    )
        
        # Try HDC matrix translation
        if self._matrix is None:
            self._matrix = get_language_matrix()
        
        if self._matrix and target_lang in self._matrix.language_anchors:
            return FallbackTranslationResult(
                text=f"[{target_lang}] {text}",
                source_lang=source_lang,
                target_lang=target_lang,
                backend="hdc_fallback",
                confidence=0.3
            )
        
        return FallbackTranslationResult(
            text=text,
            source_lang=source_lang,
            target_lang=target_lang,
            backend="hdc_fallback",
            confidence=0.0
        )
    
    def get_supported_languages(self) -> List[str]:
        """Get list of supported languages."""
        return list(LANGUAGE_CODES.keys())


_global_fallback: Optional[OfflineFallback] = None


def get_offline_fallback() -> OfflineFallback:
    global _global_fallback
    if _global_fallback is None:
        _global_fallback = OfflineFallback()
    return _global_fallback