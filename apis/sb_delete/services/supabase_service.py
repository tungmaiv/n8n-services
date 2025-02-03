# apis/data_management_api/services/supabase_service.py
import os
from supabase import create_client, Client
from typing import Tuple

class SupabaseService:
    """Service for handling Supabase operations"""
    def __init__(self):
        self.supabase: Client = create_client(
            os.getenv('SUPABASE_HOST'),
            os.getenv('SUPABASE_KEY')
        )

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
                return deleted_count, "success", f"Successfully deleted {deleted_count} rows from {table_name}"
            return 0, "success", f"No rows deleted from {table_name}"
            
        except Exception as e:
            return 0, "error", str(e)