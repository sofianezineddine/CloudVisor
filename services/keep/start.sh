#!/bin/bash
# Keep service entrypoint for CloudVisor integration
set -e

echo "Starting Keep service for CloudVisor on port ${PORT:-8007}..."

# Start the CloudVisor → Keep alert bridge consumer in the background
# This consumes from Kafka topic 'cloudvisor.alerts' and pushes to Keep's /alerts/event
python /app/cloudvisor_consumer.py &
CONSUMER_PID=$!
echo "CloudVisor alert consumer started (PID: $CONSUMER_PID)"

# Trap signals to cleanly shut down both processes
cleanup() {
  echo "Shutting down..."
  kill $CONSUMER_PID 2>/dev/null || true
  wait $CONSUMER_PID 2>/dev/null || true
  exit 0
}
trap cleanup SIGTERM SIGINT

# Start gunicorn (the main Keep API server)
exec "$@"
