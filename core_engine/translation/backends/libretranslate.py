"""
Hardwareless AI — LibreTranslate Backend
Open source, self-hosted, 40+ languages
"""
import asyncio
import random
import logging
from typing import Optional, Any, Dict
from contextlib import asynccontextmanager

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

logger = logging.getLogger("hardwareless.resilience")

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
        
        # Circuit breaker for resilience
        from core_engine.resilience import CircuitBreaker, CircuitBreakerConfig, CircuitBreakerMiddleware
        self._breaker = CircuitBreaker(
            "libretranslate",
            CircuitBreakerConfig(
                failure_threshold=5,
                recovery_timeout_seconds=60.0,
                slow_call_threshold_seconds=10.0
            )
        )
        self._breaker_middleware = CircuitBreakerMiddleware("libretranslate")
        # Wrap raw translate with circuit breaker
        self._translate_guarded = self._breaker_middleware(self.translate_raw)

    async def _get_session(self):
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def translate_raw(
        self,
        text: str,
        source_lang: str = "auto",
        target_lang: str = "en"
    ) -> TranslationResult:
        """Raw translate with retry/backoff — called through circuit breaker."""
        try:
            session = await self._get_session()
            
            payload = {
                "q": text,
                "source": "auto" if source_lang == "auto" else source_lang,
                "target": target_lang,
                "format": "text"
            }

            max_retries = 3
            for attempt in range(max_retries):
                try:
                    async with session.post(
                        f"{self.endpoint}/translate",
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=self.timeout)
                    ) as resp:
                        if resp.status == 429:
                            if attempt == max_retries - 1:
                                logger.warning(
                                    f"LibreTranslate rate limit exceeded for '{text[:50]}...' after {max_retries} retries"
                                )
                                raise Exception(f"LibreTranslate rate limit exceeded")
                            
                            base_delay = 2 ** attempt
                            jitter = random.uniform(0, 1)
                            delay = base_delay + jitter
                            await asyncio.sleep(delay)
                            continue
                        
                        if resp.status != 200:
                            logger.warning(
                                f"LibreTranslate returned status {resp.status} for '{text[:50]}...'"
                            )
                            raise Exception(f"LibreTranslate returned {resp.status}")
                        
                        data = await resp.json()
                        return TranslationResult(
                            text=data.get("translatedText", text),
                            source_lang=source_lang,
                            target_lang=target_lang,
                            backend=BackendType.LIBRETRANSLATE.value
                        )
                except asyncio.TimeoutError:
                    if attempt == max_retries - 1:
                        raise
                    jitter = random.uniform(0, 1)
                    await asyncio.sleep(1 + jitter)
                except aiohttp.ClientError as e:
                    if attempt == max_retries - 1:
                        raise Exception(f"LibreTranslate connection failed: {e}")
                    jitter = random.uniform(0, 1)
                    await asyncio.sleep(1 + jitter)
        except Exception as e:
            return TranslationResult(
                text=text,
                source_lang=source_lang,
                target_lang=target_lang,
                backend=BackendType.LIBRETRANSLATE.value,
                confidence=0.0
            )
    
    async def translate(
        self,
        text: str,
        source_lang: str = "auto",
        target_lang: str = "en"
    ) -> TranslationResult:
        """Public translate method protected by circuit breaker."""
        return await self._translate_guarded(text, source_lang, target_lang)

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