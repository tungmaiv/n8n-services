# apis/supabase_api/services/supabase_service.py
from typing import Tuple
import os
from postgrest.exceptions import APIError
from supabase import create_client, Client
from shared.logging.logger import APILogger

logger = APILogger("supabase_api").get_logger()

class SupabaseService:
    """Service for handling Supabase operations"""
    def __init__(self):
        host = os.getenv('SUPABASE_HOST')
        key = os.getenv('SUPABASE_KEY')
        
        if not host or not key:
            raise ValueError("SUPABASE_HOST and SUPABASE_KEY environment variables must be set")
            
        self.supabase: Client = create_client(host, key)

    async def delete_rows(self, table_name: str, col_name: str, filter_value: str) -> Tuple[int, str, str]:
        """
        Delete rows from Supabase table based on filter
        Returns: (deleted_count, status, message)
        """
        try:
            # Execute delete operation
            result = self.supabase.table(table_name)\
                .delete()\
                .eq(col_name, filter_value)\
                .execute()
            
            # Get count of deleted rows
            deleted_count = len(result.data) if result.data else 0
            
            # Prepare response
            if deleted_count > 0:
                message = f"Successfully deleted {deleted_count} rows from {table_name}"
                logger.info(message, extra={
                    'table': table_name,
                    'column': col_name,
                    'deleted_count': deleted_count
                })
            else:
                message = f"No rows deleted from {table_name}"
                logger.info(message, extra={
                    'table': table_name,
                    'column': col_name
                })
            
            return deleted_count, "success", message

        except APIError as e:
            error_message = f"Supabase API error: {str(e)}"
            logger.error(error_message, extra={
                'table': table_name,
                'column': col_name,
                'error': str(e)
            })
            return 0, "error", error_message
            
        except Exception as e:
            error_message = f"Error deleting rows: {str(e)}"
            logger.error(error_message, extra={
                'table': table_name,
                'column': col_name,
                'error': str(e)
            })
            return 0, "error", error_message