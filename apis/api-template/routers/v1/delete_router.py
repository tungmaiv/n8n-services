# apis/api1/routes/v1/delete_route.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import os
from supabase import create_client, Client
from shared.logging.logger import APILogger
from shared.monitoring.metrics import APIMetrics
import time

router = APIRouter()
logger = APILogger().get_logger()
metrics = APIMetrics("supabase_delete_api")

class DeleteRequest(BaseModel):
    tableName: str
    colName: str
    filter: str

class DeleteResponse(BaseModel):
    deleted_count: int
    status: str
    message: str

@router.delete("/delete", response_model=DeleteResponse)
async def delete_rows(request: DeleteRequest):
    start_time = time.time()
    
    try:
        # Initialize Supabase client
        supabase: Client = create_client(
            os.getenv("SUPABASE_HOST"),
            os.getenv("SUPABASE_KEY")
        )
        
        # Log the delete operation request
        logger.info(
            f"Attempting to delete rows from {request.tableName} "
            f"where {request.colName} = {request.filter}"
        )
        
        # Perform the delete operation
        result = supabase.table(request.tableName)\
            .delete()\
            .eq(request.colName, request.filter)\
            .execute()
            
        # Get the count of deleted rows
        deleted_count = len(result.data) if result.data else 0
        
        # Prepare the response message
        if deleted_count > 0:
            message = f"Successfully deleted {deleted_count} rows from {request.tableName}"
            status = "success"
        else:
            message = f"No rows deleted from {request.tableName}"
            status = "success"
            
        # Log the success
        logger.info(message)
        
        # Track metrics
        metrics.track_request("/delete", "DELETE", "success")
        
        response = DeleteResponse(
            deleted_count=deleted_count,
            status=status,
            message=message
        )
        
    except Exception as e:
        # Log the error
        logger.error(f"Error deleting rows: {str(e)}")
        
        # Track error metrics
        metrics.track_request("/delete", "DELETE", "error")
        
        response = DeleteResponse(
            deleted_count=0,
            status="error",
            message=str(e)
        )
    
    finally:
        # Track request latency
        metrics.request_latency.labels(
            service="supabase_delete_api",
            endpoint="/delete"
        ).observe(time.time() - start_time)
    
    return response