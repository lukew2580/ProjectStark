"""
Hardwareless AI — MTranServer Backend
Low resource, fast (~50ms), offline-capable translation server
"""
import os
import asyncio
from typing import Optional

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

from ..registry import BackendType, TranslationResult


class MTranServerBackend:
    """
    Connects to MTranServer (npx mtranserver@latest)
    - Fastest backend (~50ms response)
    - Low memory footprint
    - Good for major language pairs
    """
    def __init__(self, endpoint: str = "http://127.0.0.1:8080", timeout: float = 30.0):
        if not AIOHTTP_AVAILABLE:
            raise ImportError("aiohttp required. Run: pip install aiohttp")
        
        self.endpoint = endpoint
        self.timeout = timeout
        self._session = None

    async def _get_session(self):
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def translate(
        self,
        text: str,
        source_lang: str = "auto",
        target_lang: str = "en"
    ) -> TranslationResult:
        session = await self._get_session()
        
        lang_map = self._map_lang(source_lang, target_lang)
        
        payload = {
            "text": text,
            "from": lang_map["from"],
            "to": lang_map["to"]
        }

        try:
            async with session.post(
                f"{self.endpoint}/translate",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as resp:
                if resp.status != 200:
                    raise Exception(f"MTranServer returned {resp.status}")
                
                data = await resp.json()
                return TranslationResult(
                    text=data.get("result", text),
                    source_lang=source_lang,
                    target_lang=target_lang,
                    backend=BackendType.MTRANSERVER.value
                )
        except aiohttp.ClientError as e:
            raise Exception(f"MTranServer connection failed: {e}")

    def _map_lang(self, source: str, target: str) -> dict:
        lang_codes = {
            "en": "en", "zh": "zh", "ja": "ja", "ko": "ko",
            "es": "es", "fr": "fr", "de": "de", "ru": "ru",
            "ar": "ar", "pt": "pt", "it": "it", "nl": "nl",
            "pl": "pl", "tr": "tr", "vi": "vi", "th": "th",
            "id": "id", "ms": "ms", "hi": "hi", "auto": "auto"
        }
        
        return {
            "from": lang_codes.get(source, source),
            "to": lang_codes.get(target, target)
        }

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()