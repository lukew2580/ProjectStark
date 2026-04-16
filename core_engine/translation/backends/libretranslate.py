"""
Hardwareless AI — LibreTranslate Backend
Open source, self-hosted, 40+ languages
"""
import asyncio
from typing import Optional

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

from ..registry import BackendType, TranslationResult


class LibreTranslateBackend:
    """
    Connects to LibreTranslate (self-hosted)
    - 40+ languages supported
    - Good quality, open source
    - Requires LibreTranslate server running
    """
    def __init__(self, endpoint: str = "http://127.0.0.1:5000", timeout: float = 30.0):
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
        
        payload = {
            "q": text,
            "source": "auto" if source_lang == "auto" else source_lang,
            "target": target_lang,
            "format": "text"
        }

        try:
            async with session.post(
                f"{self.endpoint}/translate",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as resp:
                if resp.status != 200:
                    raise Exception(f"LibreTranslate returned {resp.status}")
                
                data = await resp.json()
                return TranslationResult(
                    text=data.get("translatedText", text),
                    source_lang=source_lang,
                    target_lang=target_lang,
                    backend=BackendType.LIBRETRANSLATE.value
                )
        except aiohttp.ClientError as e:
            raise Exception(f"LibreTranslate connection failed: {e}")

    async def get_languages(self) -> list:
        session = await self._get_session()
        try:
            async with session.get(
                f"{self.endpoint}/languages",
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
        except:
            pass
        return []

    async def detect_language(self, text: str) -> Optional[str]:
        session = await self._get_session()
        try:
            async with session.post(
                f"{self.endpoint}/detect",
                json={"q": text},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data:
                        return data[0].get("confidence")
        except:
            pass
        return None

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()