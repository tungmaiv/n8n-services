from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
import os
import logging
import nltk
import textwrap
from enum import Enum

nltk.download('punkt')
from nltk.tokenize import sent_tokenize

router = APIRouter()
logger = logging.getLogger("text_splitter")

class SplitStrategy(Enum):
    PARAGRAPH = "paragraph"
    SENTENCE = "sentence"
    WORD = "word"

class TextInput(BaseModel):
    text: str
    chunk_size: int = int(os.getenv("CHUNK_SIZE", 300))
    overlap_size: int = int(os.getenv("OVERLAP_SIZE", 50))
    strategy: SplitStrategy = SplitStrategy.PARAGRAPH

class ChunksOutput(BaseModel):
    chunks: List[str]
    total_chunks: int
    oversized_chunks: int

class TextSplitter:
    MIN_CHUNK_SIZE = 10

    def __init__(self, chunk_size: int, overlap_size: int, strategy: SplitStrategy = SplitStrategy.PARAGRAPH):
        self.validate_params(chunk_size, overlap_size)
        self.chunk_size = chunk_size
        self.overlap_size = overlap_size
        self.strategy = strategy
        self.logger = logging.getLogger("text_splitter")

    def validate_params(self, chunk_size: int, overlap_size: int):
        if chunk_size < self.MIN_CHUNK_SIZE:
            raise ValueError(f"Chunk size must be at least {self.MIN_CHUNK_SIZE}, got {chunk_size}")
        if overlap_size < 0:
            raise ValueError(f"Overlap size cannot be negative, got {overlap_size}")
        if overlap_size >= chunk_size:
            raise ValueError(f"Overlap size ({overlap_size}) must be smaller than chunk size ({chunk_size})")

    def split(self, text: str) -> List[str]:
        if not text.strip():
            return []
        
        if self.strategy == SplitStrategy.PARAGRAPH:
            units = text.split('\n\n')
        elif self.strategy == SplitStrategy.SENTENCE:
            units = sent_tokenize(text)
        else:
            units = textwrap.wrap(text, width=self.chunk_size)
        
        return self._create_chunks(units)

    def _create_chunks(self, units: List[str]) -> List[str]:
        chunks = []
        current_chunk = []
        current_length = 0

        for unit in units:
            unit_length = len(unit)

            if unit_length > self.chunk_size:
                if current_chunk:
                    chunks.append(" ".join(current_chunk))
                chunks.append(unit)
                self.logger.warning(f"Oversized unit detected ({unit_length} chars, max {self.chunk_size})")
                current_chunk, current_length = [], 0
                continue

            if current_length + unit_length <= self.chunk_size:
                current_chunk.append(unit)
                current_length += unit_length
            else:
                chunks.append(" ".join(current_chunk))
                current_chunk, current_length = [unit], unit_length

        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return self._add_overlap(chunks)

    def _add_overlap(self, chunks: List[str]) -> List[str]:
        if len(chunks) <= 1:
            return chunks
        
        result = [chunks[0]]
        for i in range(1, len(chunks)):
            overlap = chunks[i-1][-self.overlap_size:]
            result.append(overlap + "\n" + chunks[i])
        
        return result

@router.post("/split", response_model=ChunksOutput)
async def split_text(input_data: TextInput):
    try:
        splitter = TextSplitter(
            chunk_size=input_data.chunk_size,
            overlap_size=input_data.overlap_size,
            strategy=input_data.strategy
        )
        
        logger.info(f"Processing text with strategy={input_data.strategy.value}, chunk_size={input_data.chunk_size}")

        chunks = splitter.split(input_data.text)
        oversized = sum(1 for chunk in chunks if len(chunk) > input_data.chunk_size)

        return ChunksOutput(
            chunks=chunks,
            total_chunks=len(chunks),
            oversized_chunks=oversized
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
