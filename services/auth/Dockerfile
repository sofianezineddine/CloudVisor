# Multi-stage build for optimized production image
FROM python:3.12-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Install shared utils package first
COPY packages/utils ./packages/utils
RUN pip install --no-cache-dir --user ./packages/utils

# Install auth service dependencies
COPY services/auth/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --user -r ./requirements.txt

# Production stage
FROM python:3.12-slim as production

# Install only runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# Copy Python packages from builder stage (including all dependencies)
COPY --from=builder --chown=appuser:appuser /root/.local /home/appuser/.local
COPY --from=builder --chown=appuser:appuser /build/packages/utils /app/packages/utils

# Copy auth service source
COPY --chown=appuser:appuser services/auth /app

# Create health check script
RUN echo '#!/bin/sh' > /usr/local/bin/healthcheck.sh && \
    echo 'curl -f http://localhost:${PORT:-8002}/health || exit 1' >> /usr/local/bin/healthcheck.sh && \
    chmod +x /usr/local/bin/healthcheck.sh && \
    chown appuser:appuser /usr/local/bin/healthcheck.sh

# Switch to non-root user
USER appuser

# Add local packages to PATH and set Python path
ENV PATH=/home/appuser/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    PORT=8002

# Health check with improved timeout and retry logic
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD /usr/local/bin/healthcheck.sh

EXPOSE 8002

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002", "--workers", "4", "--graceful-timeout", "30"]
