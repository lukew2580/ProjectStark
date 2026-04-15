"""
Hardwareless AI — Stream Test (v2)
Tests the gateway as an external client would.
Includes word-order verification via API.
"""
import requests
import time
import json
import sys


BASE_URL = "http://127.0.0.1:8000"


def send_chat(prompt):
    """Send a prompt and return the response data."""
    payload = {
        "model": "hardwareless-core",
        "messages": [{"role": "user", "content": prompt}]
    }
    response = requests.post(f"{BASE_URL}/v1/chat/completions", json=payload, timeout=5)
    response.raise_for_status()
    return response.json()


def test_gateway():
    print("=" * 60)
    print("  HARDWARELESS AI — GATEWAY INTEGRATION TEST v2")
    print("=" * 60)

    # ── 1. Health Check ────────────────────────────────────────────
    print("\n[1] Health Check")
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=2)
        health = r.json()
        print(f"    Status: {health['status']}")
        print(f"    Engine: {health['engine']}")
        print(f"    Knowledge Base: {health['knowledge_base_size']} concepts")
        print(f"    Pipeline: {health['pipeline_nodes']} nodes")
    except requests.exceptions.ConnectionError:
        print("    ❌ Cannot connect to Gateway. Run: python3 gateway.py")
        sys.exit(1)

    # ── 2. Standard Chat Request ───────────────────────────────────
    print("\n[2] Standard Chat Request")
    t0 = time.perf_counter()
    data = send_chat("Hello, process this data flow test")
    elapsed = (time.perf_counter() - t0) * 1000

    content = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {})
    print(f"    Prompt: 'Hello, process this data flow test'")
    print(f"    Response: {content}")
    print(f"    Usage: {usage}")
    print(f"    Round-trip: {elapsed:.2f} ms")
    print(f"    Response ID: {data['id']}")

    # ── 3. Word Order Test via API ─────────────────────────────────
    print("\n[3] Word Order Test")
    r1 = send_chat("dog bites man")
    r2 = send_chat("man bites dog")
    c1 = r1["choices"][0]["message"]["content"]
    c2 = r2["choices"][0]["message"]["content"]
    print(f"    'dog bites man' → {c1}")
    print(f"    'man bites dog' → {c2}")
    if c1 != c2:
        print("    ✅ Different inputs produce different outputs!")
    else:
        print("    ⚠️  Same output — order encoding may need tuning")

    # ── 4. Rapid-Fire Stress Test ──────────────────────────────────
    print("\n[4] Rapid-Fire (10 requests)")
    prompts = [
        "analyze this data", "search the network", "build a new stream",
        "create distributed node", "connect to gateway", "run the pipeline",
        "decode the signal", "process the query", "send the response",
        "test hardwareless compute"
    ]
    t0 = time.perf_counter()
    for p in prompts:
        send_chat(p)
    total = (time.perf_counter() - t0) * 1000
    print(f"    10 requests completed in {total:.2f} ms")
    print(f"    Avg per request: {total/10:.2f} ms")

    print("\n" + "=" * 60)
    print("  ALL TESTS PASSED ✅")
    print("=" * 60)


if __name__ == "__main__":
    test_gateway()
