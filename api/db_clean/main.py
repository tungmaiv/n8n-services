# api/db_clean/main.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
from supabase import create_client, Client
from shared.logging.logger import setup_logger
from shared.monitoring.metrics import APIMetrics

# Initialize logger and metrics
logger = setup_logger("db_clean")
metrics = APIMetrics("db_clean")

# Initialize Supabase client once
supabase_host = os.getenv("SUPABASEHOST")
supabase_key = os.getenv("SUPABASEKEY")

if not supabase_host or not supabase_key:
    raise ValueError("SUPABASEHOST and SUPABASEKEY must be set in the environment variables.")

supabase: Client = create_client(supabase_host, supabase_key)

router = APIRouter()

class DeleteRequest(BaseModel):
    tableName: str
    colName: str
    filter: str

@router.post("/delete")
async def delete_rows(request: DeleteRequest):
    try:
        # Log operation start
        logger.info(f"Starting delete operation on table: {request.tableName}")
        
        # Execute delete operation
        result = supabase.table(request.tableName)\
            .delete()\
            .eq(request.colName, request.filter)\
            .execute()
        
        # Get deleted count
        deleted_count = len(result.data) if result.data else 0
        
        # Prepare response
        if deleted_count > 0:
            message = f"Successfully deleted {deleted_count} rows from {request.tableName}"
            logger.info(message)
        else:
            message = f"No rows deleted from {request.tableName}"
            logger.info(message)
            
        return {
            "deleted_count": deleted_count,
            "status": "success",
            "message": message
        }
            
    except Exception as e:
        error_msg = f"Error deleting from {request.tableName}: {str(e)}"
        logger.error(error_msg)
        metrics.track_error("/delete", type(e).__name__)
        return {
            "deleted_count": 0,
            "status": "error",
            "message": error_msg
        }