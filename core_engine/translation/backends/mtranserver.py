"""
Hardwareless AI — MTranServer Backend
Low resource, fast (~50ms), offline-capable translation server
"""
import os
import asyncio
import random
import logging
from typing import Optional, Any, Dict

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

logger = logging.getLogger("hardwareless.resilience")

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
        
        # Circuit breaker for resilience
        from core_engine.resilience import CircuitBreaker, CircuitBreakerConfig, CircuitBreakerMiddleware
        self._breaker = CircuitBreaker(
            "mtranserver",
            CircuitBreakerConfig(
                failure_threshold=5,
                recovery_timeout_seconds=60.0,
                slow_call_threshold_seconds=10.0
            )
        )
        self._breaker_middleware = CircuitBreakerMiddleware("mtranserver")
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
            
            lang_map = self._map_lang(source_lang, target_lang)
            
            payload = {
                "text": text,
                "from": lang_map["from"],
                "to": lang_map["to"]
            }

            # Exponential backoff with jitter for rate limiting resilience
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    async with session.post(
                        f"{self.endpoint}/translate",
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=self.timeout)
                    ) as resp:
                        if resp.status == 429:
                            # Rate limited - exponential backoff with jitter
                            if attempt == max_retries - 1:
                                logger.warning(
                                    f"MTranServer rate limit exceeded for '{text[:50]}...' after {max_retries} retries"
                                )
                                raise Exception(f"MTranServer rate limit exceeded")
                            
                            base_delay = 2 ** attempt
                            jitter = random.uniform(0, 1)
                            delay = base_delay + jitter
                            await asyncio.sleep(delay)
                            continue
                        
                        if resp.status != 200:
                            logger.warning(
                                f"MTranServer returned status {resp.status} for '{text[:50]}...'"
                            )
                            raise Exception(f"MTranServer returned {resp.status}")
                        
                        data = await resp.json()
                        return TranslationResult(
                            text=data.get("result", text),
                            source_lang=source_lang,
                            target_lang=target_lang,
                            backend=BackendType.MTRANSERVER.value
                        )
                except asyncio.TimeoutError:
                    if attempt == max_retries - 1:
                        raise
                    jitter = random.uniform(0, 1)
                    await asyncio.sleep(1 + jitter)
                    continue
                except aiohttp.ClientError as e:
                    if attempt == max_retries - 1:
                        raise Exception(f"MTranServer connection failed: {e}")
                    jitter = random.uniform(0, 1)
                    await asyncio.sleep(1 + jitter)
                    continue
        except Exception as e:
            return TranslationResult(
                text=text,
                source_lang=source_lang,
                target_lang=target_lang,
                backend=BackendType.MTRANSERVER.value,
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