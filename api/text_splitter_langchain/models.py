# api/text_splitter_langchain/models.py
from pydantic import BaseModel, Field
from typing import List

class TextInput(BaseModel):
    text: str = Field(..., description="Input text to be split")

class ChunkInfo(BaseModel):
    text: str
    size: int
    start_position: int
    end_position: int

class TextSplitResponse(BaseModel):
    chunks: List[ChunkInfo]
    total_chunks: int
    original_text_length: int