"""
Hardwareless AI — OPUS-MT Backend
CTranslate2-powered local inference, fast encoder-decoder translation
"""
import os
import asyncio
from typing import Optional, List
from ..registry import BackendType, TranslationResult

class OpusMTBackend:
    """
    OPUS-MT via CTranslate2 for local inference
    - Clean architecture, well-documented
    - 50+ language pairs supported
    - Can run on CPU efficiently
    """
    def __init__(
        self,
        model_path: str = "models/opus-mt",
        device: str = "cpu",
        compute_type: str = "int8"
    ):
        self.model_path = model_path
        self.device = device
        self.compute_type = compute_type
        self._translator = None
        self._tokenizer = None

    async def _ensure_loaded(self):
        if self._translator is not None:
            return

        await asyncio.to_thread(self._load_model)

    def _load_model(self):
        try:
            import ctranslate2
            from transformers import AutoTokenizer

            if not os.path.exists(self.model_path):
                raise FileNotFoundError(f"Model not found at {self.model_path}")

            self._translator = ctranslate2.Translator(
                self.model_path,
                device=self.device,
                compute_type=self.compute_type
            )
            self._tokenizer = AutoTokenizer.from_pretrained(self.model_path)
        except ImportError as e:
            raise ImportError(
                "CTranslate2 not installed. Run: pip install ctranslate2 transformers sentencepiece"
            ) from e

    async def translate(
        self,
        text: str,
        source_lang: str = "auto",
        target_lang: str = "en"
    ) -> TranslationResult:
        await self._ensure_loaded()

        source_lang = "zsm" if source_lang == "ms" else source_lang
        
        lang_code = f"{source_lang}-{target_lang}" if source_lang != "auto" else target_lang
        
        def _translate_sync():
            tokens = self._tokenizer.convert_ids_to_tokens(
                self._tokenizer.encode(text)
            )
            results = self._translator.translate_batch(
                [tokens],
                target_prefix=[f"</arr> {target_lang}"] if source_lang == "auto" else None
            )
            return self._tokenizer.decode(results[0][0]["tokens"])

        result_text = await asyncio.to_thread(_translate_sync)
        
        return TranslationResult(
            text=result_text,
            source_lang=source_lang,
            target_lang=target_lang,
            backend=BackendType.OPUS_MT.value
        )

    async def translate_batch(
        self,
        texts: List[str],
        source_lang: str = "auto",
        target_lang: str = "en"
    ) -> List[TranslationResult]:
        await self._ensure_loaded()

        lang_pair = f"{source_lang}-{target_lang}" if source_lang != "auto" else target_lang

        def _translate_batch_sync():
            tokens = [
                self._tokenizer.convert_ids_to_tokens(self._tokenizer.encode(text))
                for text in texts
            ]
            results = self._translator.translate_batch(tokens)
            return [
                self._tokenizer.decode(r[0]["tokens"])
                for r in results
            ]

        result_texts = await asyncio.to_thread(_translate_batch_sync)
        
        return [
            TranslationResult(
                text=rt,
                source_lang=source_lang,
                target_lang=target_lang,
                backend=BackendType.OPUS_MT.value
            )
            for rt in result_texts
        ]

    def get_supported_pairs(self) -> List[str]:
        return [
            "en-zh", "zh-en", "en-ja", "ja-en",
            "en-es", "es-en", "en-fr", "fr-en",
            "en-de", "de-en", "en-ru", "ru-en",
            "en-ar", "ar-en", "en-pt", "pt-en",
            "en-it", "it-en", "en-nl", "nl-en",
            "en-pl", "pl-en", "en-tr", "tr-en",
            "en-vi", "vi-en", "en-th", "th-en",
            "en-id", "id-en", "en-hi", "hi-en"
        ]

    async def close(self):
        self._translator = None
        self._tokenizer = None