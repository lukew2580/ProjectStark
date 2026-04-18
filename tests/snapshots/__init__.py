"""
Quality Infrastructure — Snapshot Testing
Compares API responses against stored snapshots to detect regressions.
"""

import json
import hashlib
import time
import pathlib
import pytest
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

SNAPSHOT_DIR = pathlib.Path("tests/snapshots")
SNAPSHOT_DIR.mkdir(exist_ok=True)


@dataclass
class SnapshotMeta:
    """Metadata about a snapshot."""
    name: str
    created_at: float = field(default_factory=time.time)
    version: str = "0.3.0"
    test: str = ""
    hash: str = ""


class SnapshotAssertion:
    """
    Assert response matches recorded snapshot.
    Usage:
        snapshot = SnapshotAssertion("chat_response")
        snapshot.assert_match(response_json)
    """
    
    def __init__(self, name: str, update: bool = False):
        self.name = name
        self.update = update or bool(os.getenv("UPDATE_SNAPSHOTS"))
        self.path = SNAPSHOT_DIR / f"{name}.json"
    
    def assert_match(self, data: Dict[str, Any]) -> None:
        """Assert that data matches the stored snapshot."""
        current = json.dumps(data, sort_keys=True, indent=2)
        current_hash = hashlib.md5(current.encode()).hexdigest()
        
        if not self.path.exists() or self.update:
            # Create new snapshot
            self.path.write_text(current)
            pytest.skip(f"Snapshot created: {self.name} (hash={current_hash})")
        
        stored = self.path.read_text()
        stored_hash = hashlib.md5(stored.encode()).hexdigest()
        
        if current_hash != stored_hash:
            # Diff for debugging
            diff = self._compute_diff(stored, current)
            raise AssertionError(
                f"Snapshot mismatch for '{self.name}'.\n"
                f"Stored hash: {stored_hash}\n"
                f"Current hash: {current_hash}\n"
                f"Diff:\n{diff}"
            )
    
    def _compute_diff(self, old: str, new: str) -> str:
        old_lines = old.splitlines()
        new_lines = new.splitlines()
        import difflib
        diff = difflib.unified_diff(old_lines, new_lines, fromfile="snapshot", tofile="current", lineterm="")
        return "\n".join(diff)


# Pytest fixture
@pytest.fixture
def snapshot(request):
    """
    Pytest fixture for snapshot testing.
    Usage: snapshot.assert_match(data_dict)
    """
    test_name = request.node.name
    return SnapshotAssertion(test_name)


# Predefined snapshots for major endpoints
SNAPSHOTS = {
    "chat_response": {
        "response": "Swarm Analysis: Detected semantic alignment with cognition, intelligence, processing.",
        "proposal": None,
        "sentinel_verification": "SAFE"
    },
    "translation_response": {
        "original": "Hello world",
        "translated": "Hola mundo",
        "source_lang": "en",
        "target_lang": "es",
        "confidence": 0.94
    },
    "batch_chat_response": {
        "results": [
            {"id": "abc123", "status": "success", "response": "Swarm Analysis...", "proposal": None, "sentinel_verification": "SAFE"}
        ],
        "success_count": 1,
        "error_count": 0,
        "total_ms": 123.45
    },
}

import os

__all__ = ["SnapshotAssertion", "snapshot", "SNAPSHOTS"]
