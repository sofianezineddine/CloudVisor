FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install shared utils package
COPY packages/utils /app/packages/utils
RUN pip install --no-cache-dir /app/packages/utils

# Install copilot service dependencies
COPY services/copilot/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy copilot service source
COPY services/copilot /app

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8010/health')" || exit 1

EXPOSE 8010

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8010"]
