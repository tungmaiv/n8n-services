#!/bin/bash
set -e

# Start API1
gunicorn apis.api1.main:app \
    --bind 0.0.0.0:8000 \
    --worker-class uvicorn.workers.UvicornWorker \
    --workers 2 \
    --daemon

# Start API2
gunicorn apis.api2.main:app \
    --bind 0.0.0.0:8001 \
    --worker-class uvicorn.workers.UvicornWorker \
    --workers 2 \
    --daemon

# Start metrics server (this will run in foreground)
gunicorn apis.metrics.main:app \
    --bind 0.0.0.0:8080 \
    --worker-class uvicorn.workers.UvicornWorker \
    --workers 1