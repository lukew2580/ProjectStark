# Hardwareless AI (ProjectStark)

> A GPU/CPU-less AI framework that moves with the data flow — now with VIRUS-VDI protection.

## What Is This?

This is an experimental AI framework built on **Hyperdimensional Computing (HDC)** instead of traditional neural networks. It requires no GPU, no massive CPU, and runs in under 10MB of RAM while being **600x faster** than neural-net-style matrix multiplication.

Now includes **comprehensive security**:
- VIRUS-VDI (virus detection & eradication)
- Scam Fighter System (tech support, IRS, romance scams)
- Antivirus Integration (ClamAV, Microsoft Defender)
- Scammer Attribution (identifies malicious download sources)

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

## Security Architecture

```
User Input
    ↓
[Security Layer]     ← Shell injection, SQL injection, XSS detection
    ↓
[VIRUS-VDI]         ← HDC-based virus detection
    ↓
[Scam Fighter]       ← Tech support, IRS, romance scam detection
    ↓
[Scammer Attribution] ← Identifies malicious download sources
    ↓
[Antivirus Integration] ← ClamAV, Microsoft Defender, etc.
    ↓
[Evidence Collector] ← Legal chain of custody for court
    ↓
API Response
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

## Security Features

### VIRUS-VDI (Virus Detection & Eradication)
- HDC-based virus signature detection
- Behavioral analysis
- Automated quarantine
- Authority reporting (FBI IC3, CISA)

```bash
# Scan file
curl -X POST http://localhost:8000/v1/virus/scan/file \
  -d '{"file_path": "/path/to/file"}'

# Check attribution
curl -X POST http://localhost:8000/v1/virus/attribution/check \
  -d '{"software_hash": "abc123", "download_source": "crackwatch.com"}'
```

### Scam Fighter System
Detects: Tech Support, IRS, Lottery, Romance, Phishing, Crypto, Job, Extortion scams

```bash
# Analyze phone number
curl -X POST http://localhost:8000/v1/scam/analyze/phone \
  -d '{"phone": "1-800-555-0100"}'

# Analyze website
curl -X POST http://localhost:8000/v1/scam/analyze/website \
  -d '{"url": "http://example.com"}'
```

### Antivirus Integration
- ClamAV
- Microsoft Defender
- Multi-engine scanning

```bash
# Scan with all engines
curl -X POST http://localhost:8000/v1/antivirus/scan/single \
  -d '{"file_path": "/path/to/file"}'

# Get engine status
curl http://localhost:8000/v1/antivirus/engines
```

### Automated Scanner
- Scheduled scans (hourly, daily, weekly)
- Real-time directory monitoring
- Automatic quarantine

```bash
# Add scheduled scan
curl -X POST http://localhost:8000/v1/scanner/scheduled/add \
  -d '{"scan_id": "daily_downloads", "schedule": "daily", "target_paths": ["~/Downloads"]}'

# Run manual scan
curl -X POST http://localhost:8000/v1/scanner/run \
  -d '{"target_path": "/path/to/scan"}'
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
│   ├── brain/                # HDC operations
│   ├── translation/           # Language matrix, encoder/decoder
│   ├── pipeline/              # Data flow pipeline
│   ├── virus_guard.py         # VIRUS-VDI + Scammer Attribution
│   ├── scam_fighter.py        # Scam detection
│   ├── antivirus_integration.py # Multi-AV engine integration
│   ├── automated_scanner.py   # Scheduled/real-time scanning
│   └── security.py           # Security layer
├── gateway/
│   └── routes/              # API endpoints
└── bridges/                  # Android, iOS bridges
```

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `/v1/chat/completions` | Chat (HDC-powered) |
| `/v1/translate` | Translation |
| `/v1/virus/*` | Virus detection & attribution |
| `/v1/scam/*` | Scam detection |
| `/v1/antivirus/*` | Multi-engine scanning |
| `/v1/scanner/*` | Automated scanning |
| `/v1/skills/*` | Skills management |
| `/v1/memory/*` | Knowledge memory |
| `/health` | Health check |

## Recent Updates

- Scammer Attribution System (identifies malicious download sources)
- Antivirus Integration (ClamAV, Defender)
- Automated Scanner Daemon (scheduled/real-time)
- HDC-based virus detection
- Scam Fighter (8 scam types)
- Legal evidence chain of custody

## Roadmap

- [x] Phase 1: HDC Brain (Algorithmic Leap)
- [x] Phase 2: Plug & Play Gateway (Data Flow)
- [x] Phase 3: Security Suite (VIRUS-VDI, Scam Fighter)
- [x] Phase 4: Antivirus Integration
- [ ] Phase 5: Real P2P networking
- [ ] Phase 6: Quantum substrate hooks