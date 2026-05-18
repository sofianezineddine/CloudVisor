#!/bin/bash
# Keep service entrypoint for CloudVisor integration
set -e

echo "Starting Keep service for CloudVisor on port ${PORT:-8007}..."

# Start gunicorn directly — skip provider cache build
# (providers are loaded lazily on first request)
exec "$@"
