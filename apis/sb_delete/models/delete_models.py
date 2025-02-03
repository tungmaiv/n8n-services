# apis/data_management_api/models/delete_models.py
from pydantic import BaseModel, Field
from typing import Optional

class DeleteRequest(BaseModel):
    """Request model for delete operation"""
    tableName: str = Field(..., description="Name of the table to delete from")
    colName: str = Field(..., description="Column name to filter on")
    filter: str = Field(..., description="Filter value")

class DeleteResponse(BaseModel):
    """Response model for delete operation"""
    deleted_count: int = Field(default=0, description="Number of rows deleted")
    status: str = Field(..., description="Operation status (success/error)")
    message: str = Field(..., description="Operation message")