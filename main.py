# main.py
from fastapi import FastAPI, Request
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import os
from shared.logging.logger import setup_logger
from shared.monitoring.metrics import APIMetrics
from api.db_clean.main import router as db_clean_router
from api.text_splitter.main import router as text_splitter_router
from api.text_segmentor.main import router as text_segmentor_router
from api.docx2text.main import router as docx2text_router

# Initialize logging
logger = setup_logger("main")

# Initialize metrics
metrics = APIMetrics("n8n_services")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting application")
    yield
    logger.info("Shutting down application")

app = FastAPI(lifespan=lifespan)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Metrics endpoint
@app.get("/metrics")
async def get_metrics():
    return Response(metrics.get_metrics(), media_type="text/plain")

# Include routers for each service
app.include_router(db_clean_router, prefix="/api/db_clean")
app.include_router(text_splitter_router, prefix="/api/text_splitter")
app.include_router(text_segmentor_router, prefix="/api/text_segmentor")
app.include_router(docx2text_router, prefix="/api/docx2text")

# Middleware to track metrics
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    path = request.url.path
    method = request.method
    
    try:
        with metrics.track_time(path):
            response = await call_next(request)
            metrics.track_request(path, method, response.status_code)
            return response
    except Exception as e:
        metrics.track_error(path, type(e).__name__)
        raise

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)