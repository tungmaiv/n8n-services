# api/text_splitter_langchain/utils.py
from langchain.text_splitter import (
    RecursiveCharacterTextSplitter,
    CharacterTextSplitter,
    TokenTextSplitter
)
from typing import List, Dict
from .models import ChunkInfo

class TextSplitterService:
    def __init__(self, chunk_size: int = 300, overlap_size: int = 50):
        self.chunk_size = chunk_size
        self.overlap_size = overlap_size
        
        # Initialize different splitter types
        self.splitters = {
            "recursive": RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=overlap_size,
                length_function=len,
                is_separator_regex=False
            ),
            "character": CharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=overlap_size,
                length_function=len,
                separator="\n\n"
            ),
            "token": TokenTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=overlap_size
            )
        }

    def _get_chunk_positions(self, original_text: str, chunks: List[str]) -> List[Dict[str, int]]:
        """Calculate start and end positions for each chunk in the original text"""
        positions = []
        start_pos = 0
        
        for chunk in chunks:
            # Find the chunk in the remaining text
            chunk_start = original_text.find(chunk, start_pos)
            if chunk_start != -1:
                chunk_end = chunk_start + len(chunk)
                positions.append({
                    "start": chunk_start,
                    "end": chunk_end
                })
                start_pos = chunk_end
            else:
                # Fallback if exact match not found
                positions.append({
                    "start": start_pos,
                    "end": start_pos + len(chunk)
                })
                start_pos += len(chunk)
        
        return positions

    def _join_small_chunks(self, chunks: List[str], positions: List[Dict[str, int]]) -> List[ChunkInfo]:
        """Join consecutive chunks if their combined size is less than chunk_size"""
        joined_chunks = []
        current_chunk = ""
        current_start = 0
        
        for i, chunk in enumerate(chunks):
            if not current_chunk:
                current_chunk = chunk
                current_start = positions[i]["start"]
                continue
                
            # Check if combining would exceed chunk_size
            if len(current_chunk) + len(chunk) + 1 <= self.chunk_size:
                current_chunk += "\n" + chunk
            else:
                # Add current chunk and start new one
                joined_chunks.append(ChunkInfo(
                    text=current_chunk,
                    size=len(current_chunk),
                    start_position=current_start,
                    end_position=positions[i-1]["end"]
                ))
                current_chunk = chunk
                current_start = positions[i]["start"]
        
        # Add the last chunk
        if current_chunk:
            joined_chunks.append(ChunkInfo(
                text=current_chunk,
                size=len(current_chunk),
                start_position=current_start,
                end_position=positions[-1]["end"]
            ))
        
        return joined_chunks

    def split_text(
        self,
        text: str,
        splitter_type: str = "recursive",
        join_chunks: bool = True
    ) -> List[ChunkInfo]:
        """
        Split text using specified splitter type and create chunk info
        """
        if splitter_type not in self.splitters:
            raise ValueError(f"Invalid splitter type: {splitter_type}")
        
        # Get appropriate splitter
        splitter = self.splitters[splitter_type]
        
        # Split text
        chunks = splitter.split_text(text)
        
        # Calculate positions
        positions = self._get_chunk_positions(text, chunks)
        
        # Create chunk info objects
        chunk_info_list = [
            ChunkInfo(
                text=chunk,
                size=len(chunk),
                start_position=pos["start"],
                end_position=pos["end"]
            )
            for chunk, pos in zip(chunks, positions)
        ]
        
        # Join small chunks if requested
        if join_chunks:
            return self._join_small_chunks(chunks, positions)
        
        return chunk_info_list