FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

COPY packages/utils /app/packages/utils
RUN pip install --no-cache-dir /app/packages/utils

COPY services/api/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY services/api/ /app/

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8005/health')" || exit 1

EXPOSE 8005

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8005"]
