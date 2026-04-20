# Hardwareless AI (ProjectStark)

> A GPU/CPU-less AI framework that moves with the data flow — now with VIRUS-VDI protection.
> 
> ** Unified Full-Stack System ** — Backend (FastAPI + HDC) + Frontend (Next.js 16)

## What Is This?

This is an experimental AI framework built on **Hyperdimensional Computing (HDC)** instead of traditional neural networks. It requires no GPU, no massive CPU, and runs in under 10MB of RAM while being **600x faster** than neural-net-style matrix multiplication.

Now includes **comprehensive security**:
- VIRUS-VDI (virus detection & eradication)
- Scam Fighter System (tech support, IRS, romance scams)
- Antivirus Integration (ClamAV, Microsoft Defender)
- Scammer Attribution (identifies malicious download sources)

## Architecture

```
┌─────────────────┐     ┌─────────────────────────────────────────────────┐
│   Frontend UI   │────▶│         Backend Gateway (FastAPI)              │
│   Next.js 16    │     │  • /v1/chat/completions (OpenAI-compatible)   │
│   React 19      │     │  • /v1/stream (SSE streaming)                  │
│   TypeScript    │     │  • /v1/batch (batch endpoints)                 │
│   Tailwind CSS  │     │  • /v1/translate (70+ languages)               │
└─────────────────┘     │  • /v1/stats (real-time metrics)               │
                        │  • /health (liveness/readiness)                │
                        │  • Plugin Architecture                         │
                        │  • Intelligent Caching                         │
                        │  • Connection Pooling                          │
                        │  • Resilience (circuit breakers, bulkheads)    │
                        │  • Advanced Security (CSRF, PII, threat feeds)│
                        └───────────────┬─────────────────────────────────┘
                                        │
                    ┌───────────────────┼───────────────────┐
                    │                   │                   │
              ┌─────▼─────┐      ┌──────▼──────┐    ┌──────▼──────┐
              │   Redis   │      │  HDC Engine │    │   Plugins   │
              │  Cache    │      │ (Bipolar    │    │  (pluggable)│
              │           │      │  vectors)   │    │             │
              └───────────┘      └─────────────┘    └─────────────┘
```

## Quick Start

### Using Docker Compose (Recommended)

```bash
# Clone and navigate
cd hardwareless-ai

# Production deployment (backend + frontend + Redis)
docker-compose up -d

# Development mode (with hot-reload)
docker-compose --profile dev up
```

**Access:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

### Manual Development (No Docker)

**1. Backend setup:**
```bash
cd hardwareless-ai
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
ENVIRONMENT=development python3 -m uvicorn gateway.app:app --reload
```

**2. Frontend setup (separate terminal):**
```bash
cd frontend
npm install
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```

## API Endpoints

### Core AI Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/chat/completions` | POST | Chat completion (OpenAI-compatible) |
| `/v1/translate` | POST | Translation between 70+ languages |
| `/v1/batch/chat` | POST | Batch chat processing |
| `/v1/batch/translate` | POST | Batch translation |
| `/v1/vector` | GET | Encode text to HDC vector |
| `/v1/stream` | GET | Server-Sent Events streaming |

### Legacy Compatibility (old frontend)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/chat` | POST | Legacy chat `{question: "..."}` → `{response: "..."}` |
| `/ws/stream` | WebSocket | Legacy streaming interface |
| `/health` | GET | System health & diagnostics |

### Observability & Management
| Endpoint | Description |
|----------|-------------|
| `/v1/stats` | Real-time swarm metrics (uptime, packets, latency, stability) |
| `/v1/models` | Available models & capabilities |
| `/metrics` | Prometheus metrics (if enabled) |
| `/health` | Liveness & readiness probes |
| `/health/subsystems` | Detailed subsystem health |

### Security Endpoints
| Endpoint | Purpose |
|----------|---------|
| `/v1/virus/scan/file` | VIRUS-VDI file scanning |
| `/v1/scam/analyze/*` | Scam detection (phone, website, etc.) |
| `/v1/antivirus/scan/*` | Multi-engine AV scanning |
| `/v1/scanner/*` | Automated scanning scheduler |

## Environment Variables

### Backend (gateway)
| Variable | Default | Purpose |
|----------|---------|---------|
| `ENVIRONMENT` | `production` | `development` `staging` `production` |
| `DEV_MODE` | `0` | Enable debug toolbar & verbose logging |
| `SECURITY_HEADERS_ENABLED` | `1` | Enable security headers middleware |
| `ENABLE_FINGERPRINTING` | `1` | Enable bot fingerprinting |
| `ENABLE_REQUEST_SIGNING` | (unset) | Enable request signature verification |
| `ENABLE_GRAPHQL` | `0` | Enable GraphQL endpoint |
| `ENABLE_GRPC` | `0` | Enable gRPC endpoint |
| `CORS_ALLOW_ORIGINS` | `http://localhost:3000,http://localhost:8000` | CORS allowed origins |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection string |
| `REQUEST_SIGNING_SECRET` | (required if signing enabled) | HMAC secret for request signing |
| `VAULT_ADDR` | (unset) | HashiCorp Vault address |
| `VAULT_TOKEN` | (unset) | Vault auth token |
| `AWS_REGION` | (unset) | AWS region for Secrets Manager |

### Frontend
| Variable | Default | Purpose |
|----------|---------|---------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend API base URL |
| `NEXT_PUBLIC_REFRESH_INTERVAL` | `2000` | Dashboard refresh (ms) |
| `NEXT_PUBLIC_ENABLE_STREAMING` | `1` | Show streaming chat UI |
| `NEXT_PUBLIC_ENABLE_BATCH` | `1` | Show batch processing UI |
| `NODE_ENV` | `production` | `development` `production` |

## Configuration Profiles

The backend supports automatic profile application via `config/validator.py`:

- **development** — verbose logging, dev middleware, no rate limits
- **staging** — pre-production, CSRF enabled, moderate throttling
- **production** — full security, tight rate limits, audit logging

Set via: `ENVIRONMENT=staging` (or `development`/`production`)

## Project Structure

```
hardwareless-ai/
├── backend/                  # FastAPI gateway (now at repo root)
│   ├── gateway/
│   │   ├── app.py           # Main application + lifespan init
│   │   ├── middleware/      # Auth, rate-limit, security headers, CSRF
│   │   └── routes/          # API endpoints (v1 + legacy)
│   ├── core_engine/         # HDC brain, plugins, cache, resilience
│   ├── config/              # Settings, knowledge base, validation
│   ├── network/             # HypervectorServer (port 8888)
│   └── requirements.txt     # Python dependencies
├── frontend/                # Next.js web application
│   ├── src/
│   │   ├── app/            # Next.js app router (layout, page)
│   │   ├── components/     # SwarmChat, Stats, Visualizer
│   │   └── config/         # Env config
│   ├── public/
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml       # Full-stack orchestration
├── Dockerfile              # Backend image
├── deploy/                 # K8s, Helm, Terraform
├── tests/                  # Unit, property, load, fuzz
└── scripts/               # Setup, bootstrap, phase mgmt
```

## Unified Commands

```bash
# Backend only
python3 -m uvicorn gateway.app:app --reload

# Frontend only (dev)
cd frontend && npm run dev

# Docker Compose (prod)
docker-compose up -d

# Docker Compose (dev with hot reload)
docker-compose --profile dev up

# Full test suite
pytest tests/

# Property-based tests
pytest tests/property/

# Load testing
locust -f tests/load/locustfile.py

# Fuzzing (requires Python 3.10+)
python3 -m tests.fuzz.fuzz_input_validator
```

## Plugin System

Hardwareless AI supports pluggable backends and extensions:

- **TranslatorBackendPlugin** — swap translation engines (libretranslate, mtran, opus-mt)
- **CompressionPlugin** — alternative cognitive compressors
- **CachePlugin** — custom cache backends (RedisCluster, DynamoDB)
- **ObservabilityPlugin** — external metrics/logs exporters
- **SecurityPlugin** — custom threat intel feeds, PII redactors

Plugins are discovered via entry points (`hardwareless_ai.plugins`) or directory scan.

## Ten Expansion Phases (Completed)

All phases fully implemented and integrated:

1. ✅ **Plugin Architecture** — manifest-based discovery, dependency resolution, lifecycle management
2. ✅ **Observability** — structured logging, metrics, health aggregation, request profiling
3. ✅ **Connection Pooling & Async** — AIOHTTP pools, request batching, `@batched` decorator
4. ✅ **Intelligent Caching** — multi-tier (memory/Redis/disk), cache-aside, warming
5. ✅ **Resilience** — circuit breakers, fallbacks, bulkheads, timeout cascades
6. ✅ **Developer Experience** — dev toolbar, hot-reload knowledge base, request logger
7. ✅ **API Ecosystem** — batch, SSE, webhooks, GraphQL stub, gRPC stub
8. ✅ **Advanced Security** — CSRF, bot detection, PII redaction, vaults, threat feeds
9. ✅ **Deployment Polish** — Docker multi-stage, Helm charts, Terraform EKS, HPA
10. ✅ **Quality Infrastructure** — property tests (Hypothesis), snapshots, fuzzing (Atheris), load tests (Locust), CI/CD

## Security Features

- CSRF token validation (staging/production)
- Bot fingerprinting & behavioral scoring
- PII redaction in logs/responses
- Secrets vault integration (Env, HashiCorp Vault, AWS Secrets Manager)
- Threat intelligence feeds (IP/User-Agent blocking)
- Request signing for replay protection
- Security headers (HSTS, CSP, X-Frame-Options, etc.)
- Audit logging & anomaly detection

## Performance & Scalability

| Metric | Value |
|--------|-------|
| Vector dimensions | 10,000 |
| Memory footprint | ~9.5 MB |
| Speed (10k ops) | 32 ms |
| vs Traditional NN | **601x faster** |
| Languages supported | ~70 |
| Connection pool size | configurable (default 20) |
| Cache hit latency | <1 ms (memory) |
| Circuit breaker recovery | exponential backoff |

## License

MIT

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
## Local Models
The `models/` directory is ignored by git for large `.gguf` and `.zip` files to prevent repository bloat.
Please download the required models manually and place them in the `models/` directory.

