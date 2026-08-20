# ─────────────────────────────────────────────
# Stage 1: Build — install all dependencies
# ─────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency manifest first (layer cache: only re-installs if pyproject.toml changes)
COPY pyproject.toml .

# Install into a virtual env inside the image so we can copy it cleanly to runner stage
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir ".[dev]"

# ─────────────────────────────────────────────
# Stage 2: Runner — lean production image
# ─────────────────────────────────────────────
FROM python:3.11-slim AS runner

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Bring the pre-built venv from builder (no compiler needed in runner)
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application source
COPY . .

# Run as non-root user (security best practice)
RUN adduser --disabled-password --gecos "" appuser && chown -R appuser /app
USER appuser

EXPOSE 8000

# CMD is overridden by docker-compose for dev hot-reload.
# This CMD is for production: single worker, bind to all interfaces.
CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8000"]
