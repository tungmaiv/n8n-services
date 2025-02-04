# api/text_splitter/main.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
import os
from shared.logging.logger import setup_logger
from .utils import TextSplitter, SplitStrategy

router = APIRouter()
logger = setup_logger("text_splitter")

class TextInput(BaseModel):
    text: str
    chunk_size: int = int(os.getenv("CHUNK_SIZE", 300))
    overlap_size: int = int(os.getenv("OVERLAP_SIZE", 50))
    strategy: SplitStrategy = SplitStrategy.PARAGRAPH

class ChunksOutput(BaseModel):
    chunks: List[str]
    total_chunks: int
    oversized_chunks: int

@router.post("/split", response_model=ChunksOutput)
async def split_text(input_data: TextInput):
    logger.info(f"Processing text with strategy={input_data.strategy.value}, chunk_size={input_data.chunk_size}")
    
    try:
        splitter = TextSplitter(
            input_data.chunk_size,
            input_data.overlap_size,
            input_data.strategy
        )
        chunks = splitter.split(input_data.text)
        
        oversized = sum(1 for chunk in chunks if len(chunk) > input_data.chunk_size)
        
        logger.info(f"Split completed: {len(chunks)} chunks, {oversized} oversized")
        
        return ChunksOutput(
            chunks=chunks,
            total_chunks=len(chunks),
            oversized_chunks=oversized
        )
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error processing text: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")