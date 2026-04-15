# ProjectStark

> A GPU/CPU-less AI framework that moves with the data flow.

## What Is This?

This is an experimental AI framework built on **Hyperdimensional Computing (HDC)** instead of traditional neural networks. It requires no GPU, no massive CPU, and runs in under 10MB of RAM while being **600x faster** than neural-net-style matrix multiplication.

### The Core Idea

Traditional AI (GPT, Claude, etc.) requires billions of floating-point matrix multiplications → demands GPUs with thousands of cores.

**Hardwareless AI** replaces all of that with **bipolar binary vectors** (+1 / -1) and element-wise operations. No matrices. No gradients. No GPU.

## Architecture

```
User Prompt
    ↓
[Cognitive Compressor]  ← LeanCTX-inspired noise filter (62% word reduction)
    ↓
[Text → Hypervector]    ← Encode words into 10,000-dim bipolar vectors
    ↓
[Data Flow Pipeline]    ← AI "moves" through 5 nodes (no central hardware)
    ↓
[Hypervector → Text]    ← Decode output against knowledge base
    ↓
API Response (OpenAI-compatible JSON)
```

## Quick Start

```bash
# Install (lightweight — no TensorFlow, no PyTorch)
pip3 install -r requirements.txt

# Run the benchmark
python3 simulation.py

# Start the Plug & Play API (OpenAI-compatible)
python3 gateway.py

# Test it (in another terminal)
python3 stream_test.py
```

## Plug & Play

The gateway exposes an OpenAI-compatible `/v1/chat/completions` endpoint. Any tool that works with OpenAI, OpenClaw, or MemFactory can point to `http://localhost:8000` and just work.

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"hardwareless-core","messages":[{"role":"user","content":"Hello world"}]}'
```

## Benchmark Results

| Metric | Hardwareless AI | Traditional NN |
|--------|----------------|----------------|
| Math style | Element-wise binary | Float32 matmul |
| Speed (10k ops) | 32 ms | 19,441 ms |
| **Speedup** | **601x faster** | — |
| Memory | ~9.5 MB | Gigabytes |
| GPU required | ❌ No | ✅ Yes |
| Word order encoding | ✅ Permutation | ✅ Positional encoding |
| LeanCTX compression | 62.8% word reduction | N/A |

## Project Structure

```
hardwareless-ai/
├── config.py                  # Central config — no magic numbers
├── gateway.py                 # Plug & Play API (OpenAI-compatible)
├── simulation.py              # Full benchmark suite
├── stream_test.py             # Integration tests
├── requirements.txt           # Lightweight deps only
├── core_engine/
│   ├── __init__.py
│   ├── hdc_brain.py           # HDC brain — bind, bundle, permute, recall
│   ├── translator.py          # Text ↔ Hypervector (thread-safe, order-aware)
│   ├── compressor.py          # LeanCTX-inspired cognitive filter
│   └── swarm_node.py          # DataFlowNode + Pipeline builder
└── README.md
```

## Roadmap

- [x] Phase 1: HDC Brain (Algorithmic Leap)
- [x] Phase 2: Plug & Play Gateway (Data Flow)
- [x] Refinement: LeanCTX Compression, thread safety, word order
- [ ] Phase 3: Real P2P networking (distribute across actual devices)
- [ ] Phase 4: Quantum substrate hooks (QPU interface)
