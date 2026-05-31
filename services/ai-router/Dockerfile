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
USER ai-router

# Expose port
EXPOSE 8015

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8015/health')" || exit 1

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8015", "--workers", "2"]
