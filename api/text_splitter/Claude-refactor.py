from fastapi import APIRouter, HTTPException, Response, BackgroundTasks
from pydantic import BaseModel, validator
from typing import List, Iterator, Optional, Dict
from enum import Enum
import os
import logging
import nltk
import textwrap
from functools import lru_cache
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("text_splitter")

# Initialize NLTK data
NLTK_DATA_DIR = os.getenv('NLTK_DATA', '/tmp/nltk_data')
nltk.download('punkt', quiet=True, download_dir=NLTK_DATA_DIR)

# Router initialization
router = APIRouter()

class SplitStrategy(str, Enum):
    PARAGRAPH = "paragraph"
    SENTENCE = "sentence"
    WORD = "word"

class TextInput(BaseModel):
    text: str
    chunk_size: int = int(os.getenv("CHUNK_SIZE", 300))
    overlap_size: int = int(os.getenv("OVERLAP_SIZE", 50))
    strategy: SplitStrategy = SplitStrategy.PARAGRAPH

    class Config:
        max_str_length = 1_000_000

    @validator('text')
    def text_not_empty(cls, v):
        if not isinstance(v, str):
            raise ValueError("Input must be string")
        if not v.strip():
            raise ValueError("Text cannot be empty")
        return v.strip()

    @validator('chunk_size')
    def validate_chunk_size(cls, v):
        if v < TextSplitter.MIN_CHUNK_SIZE:
            raise ValueError(f"Chunk size must be at least {TextSplitter.MIN_CHUNK_SIZE}")
        return v

    @validator('overlap_size')
    def validate_overlap_size(cls, v, values):
        if v < 0:
            raise ValueError("Overlap size cannot be negative")
        if 'chunk_size' in values and v >= values['chunk_size']:
            raise ValueError("Overlap size must be smaller than chunk size")
        return v

class BatchTextInput(BaseModel):
    texts: List[str]
    chunk_size: int = int(os.getenv("CHUNK_SIZE", 300))
    overlap_size: int = int(os.getenv("OVERLAP_SIZE", 50))
    strategy: SplitStrategy = SplitStrategy.PARAGRAPH

class ChunksOutput(BaseModel):
    chunks: List[str]
    total_chunks: int
    oversized_chunks: int
    processing_time: float
    metadata: Optional[Dict] = None

class TextSplitter:
    MIN_CHUNK_SIZE = 10
    _executor = ThreadPoolExecutor(max_workers=os.cpu_count())

    def __init__(self, chunk_size: int, overlap_size: int, strategy: SplitStrategy = SplitStrategy.PARAGRAPH):
        self.chunk_size = chunk_size
        self.overlap_size = overlap_size
        self.strategy = strategy
        self.logger = logging.getLogger("text_splitter")

    @lru_cache(maxsize=1000)
    def _get_cached_split(self, text: str, chunk_size: int, overlap_size: int, strategy: str) -> List[str]:
        return self.split(text)

    async def split_async(self, text: str) -> List[str]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, self.split, text)

    def split(self, text: str) -> List[str]:
        try:
            if not text.strip():
                return []

            units = self._split_into_units(text)
            chunks = list(self._create_chunks(units))
            return self._add_overlap(chunks)

        except Exception as e:
            self.logger.error(f"Split failed: {str(e)}")
            raise

    def _split_into_units(self, text: str) -> List[str]:
        if self.strategy == SplitStrategy.PARAGRAPH:
            return [p for p in text.split('\n\n') if p.strip()]
        elif self.strategy == SplitStrategy.SENTENCE:
            return nltk.sent_tokenize(text)
        return textwrap.wrap(text, width=self.chunk_size)

    def _create_chunks(self, units: List[str]) -> Iterator[str]:
        current_chunk = []
        current_length = 0

        for unit in units:
            unit_length = len(unit)

            if unit_length > self.chunk_size:
                if current_chunk:
                    yield " ".join(current_chunk)
                    current_chunk, current_length = [], 0
                yield unit
                self.logger.warning(f"Oversized unit detected: {unit_length} chars")
                continue

            if current_length + unit_length <= self.chunk_size:
                current_chunk.append(unit)
                current_length += unit_length
            else:
                yield " ".join(current_chunk)
                current_chunk, current_length = [unit], unit_length

        if current_chunk:
            yield " ".join(current_chunk)

    def _add_overlap(self, chunks: List[str]) -> List[str]:
        if len(chunks) <= 1:
            return chunks

        result = [chunks[0]]
        for i in range(1, len(chunks)):
            overlap = chunks[i-1][-self.overlap_size:]
            result.append(f"{overlap}\n{chunks[i]}")
        return result

@router.post("/split", response_model=ChunksOutput)
async def split_text(
    input_data: TextInput,
    response: Response,
    background_tasks: BackgroundTasks,
    cache_control: bool = True
):
    try:
        start_time = datetime.now()
        
        splitter = TextSplitter(
            chunk_size=input_data.chunk_size,
            overlap_size=input_data.overlap_size,
            strategy=input_data.strategy
        )

        # Enable caching if requested
        if cache_control:
            response.headers["Cache-Control"] = "max-age=3600"
            chunks = splitter._get_cached_split(
                input_data.text,
                input_data.chunk_size,
                input_data.overlap_size,
                input_data.strategy.value
            )
        else:
            chunks = await splitter.split_async(input_data.text)

        processing_time = (datetime.now() - start_time).total_seconds()
        oversized = sum(1 for chunk in chunks if len(chunk) > input_data.chunk_size)

        # Log metrics in background
        background_tasks.add_task(
            logger.info,
            f"Split completed: strategy={input_data.strategy.value}, chunks={len(chunks)}, time={processing_time:.2f}s"
        )

        return ChunksOutput(
            chunks=chunks,
            total_chunks=len(chunks),
            oversized_chunks=oversized,
            processing_time=processing_time,
            metadata={
                "strategy": input_data.strategy.value,
                "chunk_size": input_data.chunk_size,
                "overlap_size": input_data.overlap_size
            }
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/batch-split")
async def batch_split(inputs: BatchTextInput) -> List[ChunksOutput]:
    tasks = [
        split_text(
            TextInput(
                text=text,
                chunk_size=inputs.chunk_size,
                overlap_size=inputs.overlap_size,
                strategy=inputs.strategy
            ),
            Response(),
            BackgroundTasks(),
            cache_control=True
        )
        for text in inputs.texts
    ]
    return await asyncio.gather(*tasks)