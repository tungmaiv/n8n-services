# api/text_splitter_langchain/models.py
from pydantic import BaseModel, Field, validator
from typing import List
import sys

class TextInput(BaseModel):
    text: str = Field(..., description="Input text to be split")
    
    @validator('text')
    def validate_text(cls, v):
        # Check if text is empty or just whitespace
        if not v.strip():
            raise ValueError("Text cannot be empty or just whitespace")
        
        # Check text length (default max 10MB of text)
        max_length = 10 * 1024 * 1024  # 10MB in characters
        if len(v.encode('utf-8')) > max_length:
            raise ValueError(f"Text length exceeds maximum allowed size of {max_length} bytes")
        
        # Validate UTF-8 encoding
        try:
            v.encode('utf-8').decode('utf-8')
        except UnicodeError:
            raise ValueError("Text contains invalid Unicode characters")
        
        return v

class ChunkValidationSettings(BaseModel):
    chunk_size: int = Field(..., gt=0)
    overlap_size: int = Field(..., ge=0)
    
    @validator('overlap_size')
    def validate_overlap(cls, v, values):
        if 'chunk_size' in values and v >= values['chunk_size']:
            raise ValueError("Overlap size must be less than chunk size")
        return v

class ChunkInfo(BaseModel):
    text: str
    size: int
    start_position: int
    end_position: int
    
    @validator('text')
    def validate_chunk_text(cls, v):
        if not v.strip():
            raise ValueError("Chunk text cannot be empty")
        return v
    
    @validator('size')
    def validate_size(cls, v, values):
        if 'text' in values and len(values['text'].encode('utf-8')) != v:
            raise ValueError("Chunk size does not match text length")
        return v
    
    @validator('end_position')
    def validate_positions(cls, v, values):
        if 'start_position' in values and v <= values['start_position']:
            raise ValueError("End position must be greater than start position")
        return v

class TextSplitResponse(BaseModel):
    chunks: List[ChunkInfo]
    total_chunks: int
    original_text_length: int
    
    @validator('chunks')
    def validate_chunks(cls, v):
        if not v:
            raise ValueError("At least one chunk must be present")
        
        # Validate chunk continuity
        for i in range(len(v) - 1):
            current_chunk = v[i]
            next_chunk = v[i + 1]
            if current_chunk.end_position > next_chunk.start_position:
                raise ValueError(f"Chunk overlap detected between chunks {i} and {i+1}")
            if current_chunk.end_position < next_chunk.start_position:
                raise ValueError(f"Gap detected between chunks {i} and {i+1}")
        
        return v
    
    @validator('total_chunks')
    def validate_total_chunks(cls, v, values):
        if 'chunks' in values and len(values['chunks']) != v:
            raise ValueError("Total chunks does not match actual number of chunks")
        return v