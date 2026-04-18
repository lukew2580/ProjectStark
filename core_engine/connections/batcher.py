"""
Core Engine — Request Batcher
Aggregates concurrent requests into batches for efficient processing.
Useful for bulk translation or compression operations.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Callable, Awaitable, Tuple
from dataclasses import dataclass, field
from collections import deque
import uuid

logger = logging.getLogger("hardwareless.batcher")


@dataclass
class BatchItem:
    """A single request waiting to be batched."""
    id: str
    payload: Any
    future: asyncio.Future
    timestamp: float = field(default_factory=time.time)


@dataclass
class BatchConfig:
    """Configuration for a batcher."""
    batch_size: int = 32          # max items per batch
    batch_timeout_ms: float = 50.0  # max wait time before flushing batch
    max_queue_size: int = 1000    # max pending items
    enable_priority: bool = False  # high-priority items skip batching


class RequestBatcher:
    """
    Generic request batcher.
    Accumulates incoming calls and flushes them as a batch to a processor function.
    """
    
    def __init__(
        self,
        processor: Callable[[List[Any]], Awaitable[List[Any]]],
        config: Optional[BatchConfig] = None,
        name: str = "batcher",
    ):
        """
        processor: async function that takes List[payload] and returns List[result]
        """
        self.processor = processor
        self.config = config or BatchConfig()
        self.name = name
        self._queue: deque[BatchItem] = deque()
        self._lock = asyncio.Lock()
        self._flush_lock = asyncio.Lock()
        self._running = False
        self._flush_task: Optional[asyncio.Task] = None
    
    async def start(self) -> None:
        """Start background flush task."""
        self._running = True
        self._flush_task = asyncio.create_task(self._flush_loop())
        logger.info(f"Batcher started: {self.name}")
    
    async def stop(self) -> None:
        """Stop batcher and flush pending items."""
        self._running = False
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        # Final flush of any remaining items
        await self.flush()
        logger.info(f"Batcher stopped: {self.name}")
    
    async def submit(self, payload: Any, priority: bool = False) -> Any:
        """
        Submit a single request.
        Returns the result (awaitable).
        """
        # Check queue size limit
        async with self._lock:
            if len(self._queue) >= self.config.max_queue_size:
                raise RuntimeError(f"Batcher queue full ({self.config.max_queue_size})")
            
            # Priority items skip batching and get immediate processing
            if priority and not self.config.enable_priority:
                # Process immediately outside of batch
                result = await self.processor([payload])
                return result[0] if result else None
            
            item = BatchItem(
                id=str(uuid.uuid4()),
                payload=payload,
                future=asyncio.get_event_loop().create_future(),
            )
            self._queue.append(item)
        
        # Trigger immediate flush if batch full
        if len(self._queue) >= self.config.batch_size:
            asyncio.create_task(self.flush())
        
        return await item.future
    
    async def flush(self) -> int:
        """
        Force flush current queue as a single batch.
        Returns number of items processed.
        """
        items_to_process: List[BatchItem] = []
        async with self._lock:
            if not self._queue:
                return 0
            items_to_process = list(self._queue)
            self._queue.clear()
        
        if not items_to_process:
            return 0
        
        try:
            payloads = [item.payload for item in items_to_process]
            results = await self.processor(payloads)
            
            # Resolve futures
            for item, result in zip(items_to_process, results):
                if not item.future.done():
                    item.future.set_result(result)
            
            logger.debug(f"Batcher flush: {self.name} processed {len(results)} items")
            return len(results)
        except Exception as e:
            # Fail all pending futures
            for item in items_to_process:
                if not item.future.done():
                    item.future.set_exception(e)
            logger.error(f"Batcher flush failed: {e}", exc_info=True)
            return 0
    
    async def _flush_loop(self) -> None:
        """Background task that periodically flushes partial batches."""
        while self._running:
            try:
                await asyncio.sleep(self.config.batch_timeout_ms / 1000.0)
                await self.flush()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Flush loop error in {self.name}: {e}")
    
    def queue_size(self) -> int:
        return len(self._queue)
    
    def is_idle(self) -> bool:
        return len(self._queue) == 0


# Batching decorator for easy wrapping of existing methods
def batched(
    batch_size: int = 32,
    timeout_ms: float = 50.0,
    max_queue: int = 1000,
):
    """
    Decorator to turn a method into a batched processor automatically.
    The decorated method receives List[arg] and returns List[result].
    Individual calls use submit() under the hood.
    """
    def decorator(func: Callable[[List[Any]], Awaitable[List[Any]]]):
        batcher = RequestBatcher(
            processor=func,
            config=BatchConfig(
                batch_size=batch_size,
                batch_timeout_ms=timeout_ms,
                max_queue_size=max_queue,
            ),
            name=func.__name__,
        )
        # Start the batcher on first use
        batcher_started = False
        
        async def wrapper(*args, **kwargs):
            nonlocal batcher_started
            if not batcher_started:
                await batcher.start()
                batcher_started = True
            # Only support single positional arg for now
            payload = args[0] if args else next(iter(kwargs.values()))
            return await batcher.submit(payload)
        
        wrapper.batcher = batcher  # type: ignore
        return wrapper
    return decorator


# Convenience batching for translation: batch multiple text requests
class TranslationBatcher:
    """
    Specialized batcher that collates multiple translation requests and sends them
    as a batch translation request to the backend.
    """
    
    def __init__(
        self,
        translate_fn: Callable[
            [str, str, str, Optional[Dict[str, Any]]],  # (text, src, tgt, opts)
            Awaitable[Tuple[str, float]]
        ],
        config: Optional[BatchConfig] = None,
    ):
        self.config = config or BatchConfig(batch_size=64, batch_timeout_ms=100)
        self.translate_fn = translate_fn
        self._batcher: Optional[RequestBatcher] = None
    
    async def start(self):
        self._batcher = RequestBatcher(
            processor=self._batch_translate,
            config=self.config,
            name="translation",
        )
        await self._batcher.start()
    
    async def _batch_translate(self, items: List[Dict[str, Any]]) -> List[Tuple[str, float]]:
        """
        Batch processor: takes list of request dicts {text, source_lang, target_lang, options}
        Returns list of (translated_text, confidence) tuples.
        """
        # Collect all texts with their metadata
        texts = [item["text"] for item in items]
        src_langs = [item.get("source_lang", "auto") for item in items]
        tgt_langs = [item.get("target_lang", "en") for item in items]
        options_list = [item.get("options", {}) for item in items]
        
        # Call provider's batch method if available, else sequential
        if hasattr(self.translate_fn, "batch_translate"):
            # Backend supports native batching
            batch_results = await self.translate_fn.batch_translate(
                texts=texts,
                source_langs=src_langs,
                target_langs=tgt_langs,
                options_list=options_list,
            )
        else:
            # Fall back to parallel individual calls (still grouped)
            import asyncio
            tasks = [
                self.translate_fn(text, src, tgt, opts)
                for text, src, tgt, opts in zip(texts, src_langs, tgt_langs, options_list)
            ]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to error results
        cleaned = []
        for i, result in enumerate(batch_results):
            if isinstance(result, Exception):
                cleaned.append((f"[ERROR: {result}]", 0.0))
            else:
                cleaned.append(result if isinstance(result, tuple) else (str(result), 1.0))
        return cleaned
    
    async def translate(
        self,
        text: str,
        source_lang: str = "auto",
        target_lang: str = "en",
        options: Optional[Dict[str, Any]] = None,
        priority: bool = False,
    ) -> Tuple[str, float]:
        if not self._batcher:
            raise RuntimeError("TranslationBatcher not started")
        payload = {
            "text": text,
            "source_lang": source_lang,
            "target_lang": target_lang,
            "options": options or {},
        }
        return await self._batcher.submit(payload, priority=priority)
    
    def queue_size(self) -> int:
        return self._batcher.queue_size() if self._batcher else 0


__all__ = [
    # Core pool
    "PoolConfig",
    "PooledConnection",
    "ConnectionPool",
    "AIOHTTPConnectionPool",
    "GenericPoolManager",
    "get_pool_manager",
    # Batching
    "BatchItem",
    "BatchConfig",
    "RequestBatcher",
    "batched",
    "TranslationBatcher",
]
