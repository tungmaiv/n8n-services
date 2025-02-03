# apis/data_management_api/main.py
from fastapi import FastAPI
from .routes.v1.delete_routes import router as delete_router
from shared.logging.logger import APILogger
from shared.monitoring.metrics import APIMetrics
import os

app = FastAPI(
    title="Data Management API",
    description="API for managing data operations in Supabase",
    version="1.0.0"
)

# Initialize services
logger = APILogger(os.getenv('SERVICE_NAME', 'data_management_api')).get_logger()
metrics = APIMetrics(os.getenv('SERVICE_NAME', 'data_management_api'))

# Include routers
app.include_router(delete_router, tags=["data"])

@app.on_event("startup")
async def startup_event():
    logger.info("Data Management API starting up")
    metrics.set_build_info("1.0.0", os.getenv('GIT_COMMIT', 'unknown'))

@app.get("/health")
async def health_check():
    return {"status": "healthy"}