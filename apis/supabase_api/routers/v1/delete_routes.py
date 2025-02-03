# apis/supabase_api/routes/v1/delete_routes.py
from fastapi import APIRouter, HTTPException
from shared.monitoring.metrics import monitor_requests, APIMetrics
from ...models.delete_models import DeleteRequest, DeleteResponse
from ...services.supabase_service import SupabaseService

router = APIRouter()
metrics = APIMetrics("supabase_api")
supabase_service = SupabaseService()

@router.post("/delete", response_model=DeleteResponse)
@monitor_requests(metrics)
async def delete_rows(request: DeleteRequest) -> DeleteResponse:
    """Delete rows from Supabase table based on filter criteria"""
    deleted_count, status, message = await supabase_service.delete_rows(
        request.tableName,
        request.colName,
        request.filter
    )
    
    if status == "error":
        raise HTTPException(status_code=500, detail=message)
        
    return DeleteResponse(
        deleted_count=deleted_count,
        status=status,
        message=message
    )