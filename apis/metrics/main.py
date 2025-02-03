# apis/metrics/main.py
from fastapi import FastAPI
from prometheus_client import generate_latest
from starlette.responses import Response

app = FastAPI(title="Metrics API")

@app.get("/metrics")
async def metrics():
    """Endpoint for exposing Prometheus metrics"""
    return Response(
        generate_latest(),
        media_type="text/plain"
    )

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}