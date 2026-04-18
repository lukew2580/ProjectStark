"""
Hardwareless AI — Environment Configuration
"""
import os
import json

# === Base Paths ===
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KNOWLEDGE_DIR = os.path.join(BASE_DIR, "config", "knowledge")

# === Vector Space ===
DIMENSIONS = 10_000  # Size of all hypervectors

# === HDC Backend Configuration ===
# Pluggable HDC backend system
# Options: "auto" (best available), "legacy" (custom numpy), "torchhd" (GPU-accelerated)
HDC_BACKEND = os.getenv("HDC_BACKEND", "auto").lower()
# TorchHD-specific: "cuda" or "cpu"
HDC_DEVICE = os.getenv("HDC_DEVICE", "cuda" if os.getenv("HDC_BACKEND") == "torchhd" else "cpu")
# TorchHD model type: MAP, BSC, HRR, FHRR
HDC_TORCHHD_MODEL = os.getenv("HDC_TORCHHD_MODEL", "MAP")
# Force CPU even if GPU available?
HDC_FORCE_CPU = os.getenv("HDC_FORCE_CPU", "0").lower() in ("1", "true", "yes")

# === Data Flow Pipeline ===
DEFAULT_NODE_COUNT = 5  # Number of nodes in the default pipeline

# === Load Knowledge Base ===
KNOWLEDGE_BASE = []
vocab_paths = [
    os.path.join(KNOWLEDGE_DIR, "base_vocabulary.json"),
    os.path.join(KNOWLEDGE_DIR, "global_lexicon.json")
]

for v_path in vocab_paths:
    if os.path.exists(v_path):
        with open(v_path, "r") as f:
            data = json.load(f)
            # If it's the global lexicon dict, flatten it
            if isinstance(data, dict):
                for lang_words in data.values():
                    KNOWLEDGE_BASE.extend(lang_words)
            else:
                KNOWLEDGE_BASE.extend(data)

# Ensure unique and consistent
KNOWLEDGE_BASE = sorted(list(set(KNOWLEDGE_BASE)))

# === Response Templates ===
RESPONSE_TEMPLATES = [
    "Processing complete. Core concepts extracted: {concepts}.",
    "Data stream analyzed across {node_count} nodes. Key signals: {concepts}.",
    "Hardwareless inference finished in {time_ms}ms. Result: {concepts}.",
]

# === Security (Phase 4) ===
SWARM_KEY = os.environ.get("SWARM_KEY")
key_path = os.path.join(BASE_DIR, ".swarm.key")
if not SWARM_KEY and os.path.exists(key_path):
    try:
        with open(key_path, "r") as f:
            SWARM_KEY = f.read().strip()
    except Exception as e:
        print(f"Warning: Could not read .swarm.key: {e}")
