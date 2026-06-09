# ─── CloudVisor AI Router Service ────────────────────────────────────────────
# Unified LLM gateway for OpenAI, OpenRouter, NVIDIA NIM, and other providers
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY services/ai-router/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY services/ai-router/app ./app

# Create non-root user
RUN groupadd -r ai-router && useradd -r -g ai-router ai-router
RUN chown -R ai-router:ai-router /app

# Create health check script
RUN echo '#!/bin/sh' > /usr/local/bin/healthcheck.sh && \
    echo 'curl -f http://localhost:${PORT:-8015}/health || exit 1' >> /usr/local/bin/healthcheck.sh && \
    chmod +x /usr/local/bin/healthcheck.sh && \
    chown ai-router:ai-router /usr/local/bin/healthcheck.sh

USER ai-router

ENV PATH=/home/ai-router/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8015

EXPOSE 8015

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD /usr/local/bin/healthcheck.sh

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8015", "--workers", "4"]
