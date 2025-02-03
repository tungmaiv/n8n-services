# apis/supabase_api/main.py
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from shared.logging.logger import APILogger
from shared.monitoring.metrics import APIMetrics
import os
from datetime import datetime

from .routers.v1 import delete_routes

# Initialize FastAPI app
app = FastAPI(
    title="Supabase Delete API",
    description="API for deleting rows from Supabase tables",
    version="1.0.0"
)

# Initialize services
logger = APILogger(os.getenv('SERVICE_NAME', 'supabase_api')).get_logger()
metrics = APIMetrics(os.getenv('SERVICE_NAME', 'supabase_api'))

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(delete_routes.router, prefix="/v1", tags=["delete"])

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = datetime.utcnow()
    
    try:
        response = await call_next(request)
        duration = (datetime.utcnow() - start_time).total_seconds()
        
        logger.info(
            "Request completed",
            extra={
                'method': request.method,
                'path': request.url.path,
                'status_code': response.status_code,
                'duration_seconds': duration
            }
        )
        return response
    except Exception as e:
        logger.error(
            "Request failed",
            extra={
                'method': request.method,
                'path': request.url.path,
                'error': str(e)
            },
            exc_info=True
        )
        raise

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}