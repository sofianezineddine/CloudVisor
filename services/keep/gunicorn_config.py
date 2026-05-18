"""
Gunicorn configuration for Keep in CloudVisor.
Overrides Keep's default config.py to skip provider preloading
which crashes due to a syntax error in anthropic_provider.py.
"""

import os
import logging

PORT = int(os.environ.get("PORT", 8007))

# Gunicorn settings
bind = f"0.0.0.0:{PORT}"
workers = int(os.environ.get("KEEP_WORKERS", 2))
worker_class = "uvicorn.workers.UvicornWorker"
timeout = 120
graceful_timeout = 30
keepalive = 5
preload_app = False  # Don't preload to avoid provider import errors


def on_starting(server):
    """Minimal on_starting — skip provider cache to avoid import errors."""
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.info("Keep server starting (CloudVisor mode)")

    # Run migrations only
    try:
        from keep.api.core.db_on_start import migrate_db, try_create_single_tenant
        from keep.api.core.dependencies import SINGLE_TENANT_UUID

        migrate_db()
        try_create_single_tenant(SINGLE_TENANT_UUID, create_default_user=False)
        logger.info("Database migrations completed")
    except Exception as e:
        logger.error(f"Migration failed: {e}")


def post_worker_init(worker):
    """Initialize logging in each worker."""
    import keep.api.logging
    logging.getLogger().handlers = []
    keep.api.logging.setup_logging()
