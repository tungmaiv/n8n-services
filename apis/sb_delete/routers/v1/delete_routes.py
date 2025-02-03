# apis/data_management_api/routes/v1/delete_routes.py
from fastapi import APIRouter, Depends
from ...models.delete_models import DeleteRequest, DeleteResponse
from ...services.supabase_service import SupabaseService
from shared.logging.logger import APILogger
from shared.monitoring.metrics import monitor_requests, APIMetrics
import os

router = APIRouter(prefix="/v1/data")
logger = APILogger(os.getenv('SERVICE_NAME', 'data_management_api')).get_logger()
metrics = APIMetrics(os.getenv('SERVICE_NAME', 'data_management_api'))

@router.post("/delete", response_model=DeleteResponse)
@monitor_requests(metrics)
async def delete_data(request: DeleteRequest, supabase_service: SupabaseService = Depends(SupabaseService)):
    """
    Delete rows from specified table based on filter
    """
    logger.info(
        "Delete request received",
        extra={
            'table': request.tableName,
            'column': request.colName,
            'operation': 'delete'
        }
    )

    try:
        # Execute delete operation
        deleted_count, status, message = await supabase_service.delete_rows(
            request.tableName,
            request.colName,
            request.filter
        )

        # Log result
        logger.info(
            "Delete operation completed",
            extra={
                'table': request.tableName,
                'deleted_count': deleted_count,
                'status': status
            }
        )

        return DeleteResponse(
            deleted_count=deleted_count,
            status=status,
            message=message
        )

    except Exception as e:
        logger.error(
            "Delete operation failed",
            extra={
                'table': request.tableName,
                'error': str(e)
            },
            exc_info=True
        )
        return DeleteResponse(
            deleted_count=0,
            status="error",
            message=str(e)
        )