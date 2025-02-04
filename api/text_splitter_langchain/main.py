# api/text_splitter_langchain/main.py
from fastapi import APIRouter, HTTPException, Query
from .utils import TextSplitterService
from .models import TextInput, TextSplitResponse
from shared.logging.logger import setup_logger
import os

# Initialize router
router = APIRouter()

# Initialize logger
logger = setup_logger("text_splitter_langchain")

@router.post("/split", response_model=TextSplitResponse)
async def split_text(
    input_data: TextInput,
    splitter_type: str = Query(
        "recursive",
        description="Type of splitter to use: recursive, character, or token"
    ),
    join_chunks: bool = Query(
        True,
        description="Whether to join smaller chunks"
    ),
):
    """
    Split input text into chunks using specified LangChain splitter
    """
    # Get configuration from environment variables
    chunk_size = int(os.getenv("CHUNK_SIZE", 300))
    overlap_size = int(os.getenv("OVERLAP_SIZE", 50))
    
    logger.info(f"Processing text split request with splitter_type={splitter_type}, join_chunks={join_chunks}")
    
    # Validate input
    if not input_data.text.strip():
        logger.error("Empty text input received")
        raise HTTPException(status_code=400, detail="Empty text input")

    try:
        # Initialize service
        service = TextSplitterService(
            chunk_size=chunk_size,
            overlap_size=overlap_size
        )
        
        # Process text based on splitter type
        chunks_info = service.split_text(
            input_data.text,
            splitter_type=splitter_type,
            join_chunks=join_chunks
        )
        
        response = TextSplitResponse(
            chunks=chunks_info,
            total_chunks=len(chunks_info),
            original_text_length=len(input_data.text)
        )
        
        logger.info(f"Successfully split text into {len(chunks_info)} chunks")
        return response

    except ValueError as e:
        logger.error(f"Value error in text splitting: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in text splitting: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")