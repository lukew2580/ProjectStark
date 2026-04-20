# Hardwareless AI — Multi-Stage Dockerfile
# Optimized for production: builder stage compiles deps, final stage minimal

# ——————————————————————————————
# Stage 1: Builder — compile dependencies
# ——————————————————————————————
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build deps
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libssl-dev \
    libffi-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Install pip tools
COPY setup.py* requirements.txt* ./
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Install Python deps
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -e . 2>/dev/null || true

# ——————————————————————————————
# Stage 2: Runtime — minimal image
# ——————————————————————————————
FROM python:3.11-slim

WORKDIR /app

# Create non-root user
RUN groupadd -r hdc && useradd -r -g hdc hdc

# Copy installed deps from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY --chown=hdc:hdc . .

# Environment
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV ENVIRONMENT=production
ENV LOG_LEVEL=WARNING
ENV SECURITY_HEADERS_ENABLED=1
ENV INPUT_VALIDATION_ENABLED=1
ENV ENABLE_REQUEST_SIGNING=1

# Runtime dirs
RUN mkdir -p /data/logs /data/cache /data/knowledge && chown -R hdc:hdc /data

# Volume mounts
VOLUME ["/data/logs", "/data/cache", "/data/knowledge"]

# Expose ports
EXPOSE 8000 50051 8888

# Switch to non-root
USER hdc

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health').read()"

# Default command (can override with custom entrypoint)
CMD ["python", "-m", "uvicorn", "gateway.app:app", "--host", "0.0.0.0", "--port", "8000"]
