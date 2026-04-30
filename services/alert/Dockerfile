FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install shared packages
COPY packages/utils /app/packages/utils
RUN pip install --no-cache-dir /app/packages/utils

# Install service dependencies
COPY services/alert/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy service source
COPY services/alert/ /app/

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8004/health')" || exit 1

EXPOSE 8004

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8004"]
