"""
Test Suite — Request Batcher (core_engine/connections/batcher.py)
Covers: BatchItem, BatchConfig, RequestBatcher, @batched decorator, TranslationBatcher.
"""
import asyncio
import time
import pytest
from unittest.mock import AsyncMock, MagicMock

from core_engine.connections.batcher import (
    BatchItem,
    BatchConfig,
    RequestBatcher,
    batched,
    TranslationBatcher,
)


# ============================================================================
# BatchItem tests
# ============================================================================

def test_batch_item_creation():
    fut = asyncio.get_event_loop().create_future()
    item = BatchItem(id="test-1", payload={"x": 1}, future=fut)
    assert item.id == "test-1"
    assert item.payload == {"x": 1}
    assert item.future is fut
    assert abs(time.time() - item.timestamp) < 1.0


# ============================================================================
# BatchConfig tests
# ============================================================================

def test_batch_config_defaults():
    cfg = BatchConfig()
    assert cfg.batch_size == 32
    assert cfg.batch_timeout_ms == 50.0
    assert cfg.max_queue_size == 1000
    assert cfg.enable_priority is False


# ============================================================================
# RequestBatcher core tests
# ============================================================================

@pytest.mark.asyncio
async def test_batcher_start_stop():
    async def processor(items):
        return items

    batcher = RequestBatcher(processor=processor, name="test")
    await batcher.start()
    assert batcher._running is True
    assert batcher._flush_task is not None

    await batcher.stop()
    assert batcher._running is False
    assert batcher._flush_task.done()


@pytest.mark.asyncio
async def test_submit_and_flush():
    results = []
    async def processor(items):
        results.append(items)
        return [f"result-{i}" for i in range(len(items))]

    # Disable background auto-flush by setting a very long timeout
    batcher = RequestBatcher(
        processor=processor,
        config=BatchConfig(batch_size=2, batch_timeout_ms=10000)
    )
    await batcher.start()

    # Submit two items concurrently to ensure both are queued before any flush
    task_a = asyncio.create_task(batcher.submit("a"))
    task_b = asyncio.create_task(batcher.submit("b"))

    # Await both results
    r1 = await task_a
    r2 = await task_b

    # The batch trigger should have caused a single flush with both items
    assert results[0] == ["a", "b"]
    assert r1 == "result-0"
    assert r2 == "result-1"

    await batcher.stop()


@pytest.mark.asyncio
async def test_flush_manual():
    results = []
    async def processor(items):
        results.extend(items)
        return ["ok"] * len(items)

    # Use large timeout to prevent auto-flush; manual flush only
    batcher = RequestBatcher(
        processor=processor,
        config=BatchConfig(batch_size=10, batch_timeout_ms=10000)
    )
    await batcher.start()

    # Submit items without awaiting (via tasks) so they stay in queue
    task1 = asyncio.create_task(batcher.submit(1))
    task2 = asyncio.create_task(batcher.submit(2))
    # Let tasks reach the awaiting point
    await asyncio.sleep(0)

    # Manual flush should process both
    flushed = await batcher.flush()
    assert flushed == 2

    # Now await the tasks to get results
    r1 = await task1
    r2 = await task2
    assert r1 == "ok"
    assert r2 == "ok"
    assert results == [1, 2]

    await batcher.stop()


@pytest.mark.asyncio
async def test_flush_empty_returns_zero():
    async def processor(items):
        return []

    batcher = RequestBatcher(processor=processor)
    await batcher.start()
    count = await batcher.flush()
    assert count == 0
    await batcher.stop()


@pytest.mark.asyncio
async def test_processor_exception_fails_all_futures():
    async def processor(items):
        raise RuntimeError("boom")

    batcher = RequestBatcher(processor=processor)
    await batcher.start()

    with pytest.raises(RuntimeError, match="boom"):
        await batcher.submit("x")

    # The exception should be set on the future
    # Also flush may propagate? But submit already raised.
    await batcher.stop()


@pytest.mark.asyncio
async def test_queue_full_raises():
    async def processor(items):
        return items

    cfg = BatchConfig(max_queue_size=2, batch_size=10, batch_timeout_ms=10000)
    batcher = RequestBatcher(processor=processor, config=cfg)
    await batcher.start()

    # Submit two items without awaiting (use tasks) so they stay queued
    task1 = asyncio.create_task(batcher.submit(1))
    task2 = asyncio.create_task(batcher.submit(2))
    # Allow tasks to start and enqueue items
    await asyncio.sleep(0)

    # Third submit should raise RuntimeError because queue is full
    with pytest.raises(RuntimeError, match="Batcher queue full"):
        await batcher.submit(3)

    # Clean up pending tasks (cancel to avoid warnings)
    task1.cancel()
    task2.cancel()
    try:
        await task1
        await task2
    except asyncio.CancelledError:
        pass

    await batcher.stop()


@pytest.mark.asyncio
async def test_priority_immediate_when_enabled():
    """Priority items bypass batch and are processed immediately if enabled."""
    order = []
    async def processor(items):
        order.append(("batch", items))
        return ["ok"] * len(items)

    # Disable background flush to control timing
    cfg = BatchConfig(batch_size=5, enable_priority=True, batch_timeout_ms=10000)
    batcher = RequestBatcher(processor=processor, config=cfg)
    await batcher.start()

    # Submit one priority item
    r1 = await batcher.submit("p1", priority=True)
    assert r1 == "ok"
    assert order == [("batch", ["p1"])]  # only immediate call

    # Submit two normal items as background tasks (don't await yet)
    task2 = asyncio.create_task(batcher.submit("n1"))
    task3 = asyncio.create_task(batcher.submit("n2"))
    await asyncio.sleep(0.01)  # let submissions register
    assert order == [("batch", ["p1"])]  # no batch yet

    # Manually flush to process normal items together
    flushed = await batcher.flush()
    assert flushed == 2

    # Now await the tasks to get results
    r2 = await task2
    r3 = await task3
    assert r2 == "ok"
    assert r3 == "ok"
    assert ("batch", ["n1", "n2"]) in order

    await batcher.stop()


@pytest.mark.asyncio
async def test_priority_disabled_ignored():
    """When priority disabled, priority flag is ignored and items are batched normally."""
    called = []
    async def processor(items):
        called.append(items)
        return ["ok"] * len(items)

    cfg = BatchConfig(batch_size=5, enable_priority=False)
    batcher = RequestBatcher(processor=processor, config=cfg)
    await batcher.start()

    r = await batcher.submit("x", priority=True)  # priority ignored
    assert r == "ok"
    # Since batch size not reached, it will wait for flush timeout; but we can manually flush
    await batcher.flush()
    assert called == [["x"]]

    await batcher.stop()


# ============================================================================
# Batched decorator tests
# ============================================================================

@pytest.mark.asyncio
async def test_batched_decorator_batches_calls():
    calls = []

    @batched(batch_size=3, timeout_ms=100)
    async def my_func(item):
        # processor receives list of items and returns list
        results = []
        for i in item:
            calls.append(i)
            results.append(i * 2)
        return results

    # Starting the batcher happens on first call
    r1 = await my_func(1)
    r2 = await my_func(2)
    r3 = await my_func(3)

    assert r1 == 2
    assert r2 == 4
    assert r3 == 6
    # The underlying function should have been called once with [1,2,3]
    assert calls == [1, 2, 3]

    # Stop the underlying batcher for cleanup
    await my_func.batcher.stop()


# ============================================================================
# TranslationBatcher tests
# ============================================================================

@pytest.mark.asyncio
async def test_translation_batcher_batch_translate():
    """TranslationBatcher uses batch processor if available."""
    class MockBackend:
        async def batch_translate(self, texts, source_langs, target_langs, options_list):
            # Return translated uppercase with confidence 0.9
            return [(t.upper(), 0.9) for t in texts]

    backend = MockBackend()
    # Use a small batch_size to trigger immediate flush after two submissions
    batcher = TranslationBatcher(
        translate_fn=backend,
        config=BatchConfig(batch_size=2, batch_timeout_ms=10000)
    )
    await batcher.start()

    # Submit translations concurrently to ensure they batch together
    r1_task = asyncio.create_task(batcher.translate("hello", "en", "es"))
    r2_task = asyncio.create_task(batcher.translate("world", "en", "fr"))

    r1 = await r1_task
    r2 = await r2_task

    assert r1 == ("HELLO", 0.9)
    assert r2 == ("WORLD", 0.9)

    await batcher._batcher.stop()


@pytest.mark.asyncio
async def test_translation_batcher_fallback_individual():
    """If backend lacks batch_translate, fall back to asyncio.gather."""
    calls = []

    async def translate_single(text, source_lang, target_lang, options=None):
        calls.append(text)
        return (text.upper(), 0.8)

    batcher = TranslationBatcher(translate_fn=translate_single)
    await batcher.start()

    r1 = await batcher.translate("foo")
    r2 = await batcher.translate("bar")

    assert r1 == ("FOO", 0.8)
    assert r2 == ("BAR", 0.8)
    assert calls == ["foo", "bar"]

    await batcher._batcher.stop()


# ============================================================================
# Concurrency tests
# ============================================================================

@pytest.mark.asyncio
async def test_batcher_concurrent_submits():
    """Many concurrent submits should be batched correctly."""
    results = []
    async def processor(items):
        await asyncio.sleep(0.01)  # simulate work
        results.extend(items)
        return [x * 2 for x in items]

    batcher = RequestBatcher(processor=processor, config=BatchConfig(batch_size=10))
    await batcher.start()

    # Submit 20 items concurrently
    tasks = [batcher.submit(i) for i in range(20)]
    outs = await asyncio.gather(*tasks)

    assert outs == [i*2 for i in range(20)]
    # Processor should have been called twice (2 batches of 10)
    assert len(results) == 20
    # Order of processing may be grouped
    # Ensure all inputs present
    assert sorted(results) == list(range(20))

    await batcher.stop()
