# ─── Build stage ────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy shared utils package
COPY packages/utils ./packages/utils
RUN pip install --no-cache-dir --user ./packages/utils

# Copy connector service requirements and install
COPY services/connector/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --user -r ./requirements.txt

# ─── Runtime stage ──────────────────────────────────────────────
FROM python:3.12-slim

WORKDIR /app

# Install runtime system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy installed Python packages from builder
COPY --from=builder --chown=appuser:appuser /root/.local /home/appuser/.local

# Copy Avro schemas (needed by avro_serializer.py at runtime)
COPY --chown=appuser:appuser packages/kafka-schemas /app/packages/kafka-schemas

# Copy connector service source
COPY --chown=appuser:appuser services/connector /app

# Create health check script
RUN echo '#!/bin/sh' > /usr/local/bin/healthcheck.sh && \
    echo 'curl -f http://localhost:${PORT:-8000}/health || exit 1' >> /usr/local/bin/healthcheck.sh && \
    chmod +x /usr/local/bin/healthcheck.sh && \
    chown appuser:appuser /usr/local/bin/healthcheck.sh

USER appuser

# Environment variables
ENV PATH=/home/appuser/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD /usr/local/bin/healthcheck.sh

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2", "--graceful-timeout", "30"]
