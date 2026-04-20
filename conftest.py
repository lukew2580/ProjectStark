"""
Hardwareless AI — Root pytest configuration.

Sets asyncio_mode="auto" so all async test functions are automatically
treated as asyncio coroutines without needing @pytest.mark.asyncio on each one.
This is required for pytest-asyncio >= 0.21.
"""
import pytest


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "slow: mark test as slow-running")
    config.addinivalue_line("markers", "gpu: mark test as requiring GPU")


# ── asyncio mode ──────────────────────────────────────────────────────────────
# Required for pytest-asyncio >= 0.21 without per-test @pytest.mark.asyncio
# Can also be set via pytest.ini: asyncio_mode = auto
# We set it here to keep config in one place.
