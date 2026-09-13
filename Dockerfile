# ==============================================================================
# Stage 1: Build & Dependencies
# ==============================================================================
FROM python:3.12-slim AS builder

WORKDIR /build

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
RUN python -m pip install --upgrade pip setuptools wheel
RUN pip install --no-cache-dir .

# ==============================================================================
# Stage 2: Minimal Distroless / Hardened Runner
# ==============================================================================
FROM python:3.12-slim AS runner

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    APP_ENV=production

# Install runtime system libraries (libpq for PostgreSQL, curl for healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-privileged system user for container security
RUN groupadd -g 10001 docuchat && \
    useradd -u 10001 -g docuchat -m -s /bin/bash appuser

# Copy installed python site-packages and binaries from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application source code
COPY --chown=appuser:docuchat src ./src
COPY --chown=appuser:docuchat pyproject.toml README.md ./

# Create data directories and establish ownership
RUN mkdir -p /app/data /app/logs && chown -R appuser:docuchat /app

USER appuser

EXPOSE 8000

# Docker native healthcheck polling API gateway
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Launch Enterprise Gateway with uvicorn
CMD ["uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
