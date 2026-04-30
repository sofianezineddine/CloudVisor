# ─── Build stage ────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy shared utils package
COPY packages/utils /build/packages/utils
RUN pip install --no-cache-dir /build/packages/utils

# Copy connector service requirements and install
COPY services/connector/requirements.txt /build/requirements.txt
RUN pip install --no-cache-dir -r /build/requirements.txt

# ─── Runtime stage ──────────────────────────────────────────────
FROM python:3.12-slim

WORKDIR /app

# Install runtime system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy connector service source
COPY services/connector /app

# Set working directory
WORKDIR /app

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Expose port
EXPOSE 8000

# Run the service
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
