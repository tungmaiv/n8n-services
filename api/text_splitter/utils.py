# api/text_splitter/utils.py
from enum import Enum
import re
from typing import List, Pattern
import logging

class SplitStrategy(Enum):
    PARAGRAPH = "paragraph"
    SENTENCE = "sentence"
    WORD = "word"

class TextSplitter:
    def __init__(self, chunk_size: int, overlap_size: int, 
                 strategy: SplitStrategy = SplitStrategy.PARAGRAPH,
                 paragraph_pattern: Pattern = re.compile(r'\n\s*\n|(?<=[.!?])\s+(?=[A-Z])')):
        self.validate_params(chunk_size, overlap_size)
        self.chunk_size = chunk_size
        self.overlap_size = overlap_size
        self.strategy = strategy
        self.paragraph_pattern = paragraph_pattern
        self.logger = logging.getLogger("text_splitter")

    def validate_params(self, chunk_size: int, overlap_size: int):
        if chunk_size <= 0:
            raise ValueError("Chunk size must be positive")
        if overlap_size < 0:
            raise ValueError("Overlap size cannot be negative")
        if overlap_size >= chunk_size:
            raise ValueError("Overlap size must be less than chunk size")

    def split(self, text: str) -> List[str]:
        if not text.strip():
            return []

        if self.strategy == SplitStrategy.PARAGRAPH:
            units = self._split_paragraphs(text)
        elif self.strategy == SplitStrategy.SENTENCE:
            units = self._split_sentences(text)
        else:  # WORD
            units = self._split_words(text)

        return self._create_chunks(units)

    def _split_paragraphs(self, text: str) -> List[str]:
        return [p.strip() for p in self.paragraph_pattern.split(text) if p.strip()]

    def _split_sentences(self, text: str) -> List[str]:
        sentence_pattern = re.compile(r'(?<=[.!?])\s+(?=[A-Z])')
        return [s.strip() for s in sentence_pattern.split(text) if s.strip()]

    def _split_words(self, text: str) -> List[str]:
        return text.split()

    def _create_chunks(self, units: List[str]) -> List[str]:
        chunks = []
        current_chunk = []
        current_length = 0

        for unit in units:
            unit_length = len(unit)
            
            if unit_length > self.chunk_size:
                if current_chunk:
                    chunks.append('\n'.join(current_chunk))
                chunks.append(unit)
                self.logger.warning(f"Oversized unit detected: {unit_length} characters (chunk_size: {self.chunk_size})")
                current_chunk = []
                current_length = 0
                continue

            if current_length + unit_length <= self.chunk_size:
                current_chunk.append(unit)
                current_length += unit_length
            else:
                chunks.append('\n'.join(current_chunk))
                current_chunk = [unit]
                current_length = unit_length

        if current_chunk:
            chunks.append('\n'.join(current_chunk))

        return self._add_overlap(chunks)

    def _add_overlap(self, chunks: List[str]) -> List[str]:
        if len(chunks) <= 1:
            return chunks

        result = []
        for i in range(len(chunks)):
            if i > 0:
                current = chunks[i-1][-self.overlap_size:] + "\n" + chunks[i]
            else:
                current = chunks[i]
            result.append(current)

        return result