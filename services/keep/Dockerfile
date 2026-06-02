FROM python:3.11-slim AS base

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONFAULTHANDLER=1 \
    PYTHONHASHSEED=random \
    PYTHONUNBUFFERED=1

RUN groupadd -g 1000 keep && \
    useradd -u 1000 -g keep -s /bin/bash -m keep

WORKDIR /app

# --- Builder stage ---
FROM base AS builder

ENV PIP_DEFAULT_TIMEOUT=100 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VERSION=1.8.3

RUN pip install "poetry==$POETRY_VERSION"
RUN python -m venv /venv

# Copy dependency files
COPY keep/pyproject.toml keep/poetry.lock ./

# Export and install dependencies
RUN poetry export -f requirements.txt --output requirements.txt --without-hashes --only main && \
    /venv/bin/python -m pip install --upgrade -r requirements.txt && \
    pip uninstall -y poetry

# Copy application source
COPY keep/keep/ ./keep/
COPY keep/ee/ ./ee/

# Install the keep package
RUN /venv/bin/pip install --use-deprecated=legacy-resolver . && \
    rm -rf /root/.cache/pip

# Remove unnecessary files from the installed package
RUN find /venv -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true && \
    find /venv -type f -name "*.pyc" -delete 2>/dev/null || true && \
    find /venv -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true && \
    find /venv -type d -name "docs" -exec rm -rf {} + 2>/dev/null || true && \
    find /venv -type d -name "examples" -exec rm -rf {} + 2>/dev/null || true && \
    find /venv -type f -name "*.rego" -delete 2>/dev/null || true

# --- Final stage ---
FROM base AS final

ENV PATH="/venv/bin:${PATH}" \
    VIRTUAL_ENV="/venv" \
    EE_PATH="ee" \
    PORT=8007

COPY --from=builder /venv /venv

# Copy entrypoint script and CloudVisor consumer bridge
COPY services/keep/start.sh /app/start.sh
COPY services/keep/cloudvisor_consumer.py /app/cloudvisor_consumer.py
COPY services/keep/gunicorn_config.py /app/gunicorn_config.py
# Copy workflow template examples (needed by /workflows/templates/query endpoint)
COPY keep/examples/workflows /examples/workflows
RUN chmod +x /app/start.sh

# Create health check script
RUN echo '#!/bin/sh' > /usr/local/bin/healthcheck.sh && \
    echo 'curl -f http://localhost:${PORT:-8007}/healthcheck || exit 1' >> /usr/local/bin/healthcheck.sh && \
    chmod +x /usr/local/bin/healthcheck.sh && \
    chown keep:keep /usr/local/bin/healthcheck.sh

# Set ownership
RUN chgrp -R 0 /app && chmod -R g=u /app && \
    chown -R keep:keep /app && \
    chown -R keep:keep /venv

USER keep

EXPOSE 8007

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD /usr/local/bin/healthcheck.sh

ENTRYPOINT ["/app/start.sh"]
CMD ["gunicorn", "keep.api.api:get_app", "-c", "/app/gunicorn_config.py"]
