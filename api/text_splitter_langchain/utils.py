# api/text_splitter_langchain/utils.py
from langchain.text_splitter import (
    RecursiveCharacterTextSplitter,
    CharacterTextSplitter,
    TokenTextSplitter
)
from typing import List, Dict
from .models import ChunkInfo, ChunkValidationSettings
import signal
import resource
import sys
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)

class TimeoutError(Exception):
    pass

class MemoryError(Exception):
    pass

@contextmanager
def time_limit(seconds):
    def signal_handler(signum, frame):
        raise TimeoutError("Processing timed out")
    
    signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)

@contextmanager
def memory_limit(max_gb):
    """
    Context manager to limit memory usage.
    Args:
        max_gb (int): Maximum memory limit in gigabytes
    """
    max_bytes = max_gb * 1024 * 1024 * 1024  # Convert GB to bytes
    # Store original limits
    original_limits = None
    
    try:
        # Get the current limits
        original_limits = resource.getrlimit(resource.RLIMIT_AS)
        
        # Set new memory limit
        resource.setrlimit(resource.RLIMIT_AS, (max_bytes, original_limits[1]))
        yield
        
    except Exception as e:
        logger.error(f"Failed to set memory limit: {str(e)}")
        raise MemoryError(f"Unable to set memory limit: {str(e)}")
        
    finally:
        # Restore original limits if they were successfully retrieved
        if original_limits is not None:
            try:
                resource.setrlimit(resource.RLIMIT_AS, original_limits)
            except Exception as e:
                logger.error(f"Failed to restore original memory limits: {str(e)}")

class TextSplitterService:
    def __init__(self, chunk_size: int = 300, overlap_size: int = 50,
                 timeout_seconds: int = 300, max_memory_gb: int = 4):
        # Validate settings
        self.settings = ChunkValidationSettings(
            chunk_size=chunk_size,
            overlap_size=overlap_size
        )
        self.timeout_seconds = timeout_seconds
        self.max_memory_gb = max_memory_gb
        
        # Initialize different splitter types
        self.splitters = {
            "recursive": RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=overlap_size,
                length_function=lambda x: len(x.encode('utf-8')),
                is_separator_regex=False
            ),
            "character": CharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=overlap_size,
                length_function=lambda x: len(x.encode('utf-8')),
                separator="\n\n"
            ),
            "token": TokenTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=overlap_size
            )
        }

    def validate_chunk_integrity(self, original_text: str, chunks: List[ChunkInfo]) -> bool:
        """Validate the integrity of chunks against the original text"""
        # Check if all text is accounted for
        reconstructed_text = ""
        last_position = 0
        
        for chunk in chunks:
            # Verify positions
            if chunk.start_position < last_position:
                raise ValueError(f"Invalid chunk position: overlap detected at position {chunk.start_position}")
            if chunk.start_position > last_position:
                raise ValueError(f"Gap detected between chunks at position {last_position}")
            
            # Verify chunk content
            original_slice = original_text[chunk.start_position:chunk.end_position]
            if original_slice != chunk.text:
                raise ValueError(f"Chunk content mismatch at position {chunk.start_position}")
            
            reconstructed_text += chunk.text
            last_position = chunk.end_position
        
        # Verify complete coverage
        if len(original_text.encode('utf-8')) != len(reconstructed_text.encode('utf-8')):
            raise ValueError("Not all text is accounted for in chunks")
        
        return True

    def _get_chunk_positions(self, original_text: str, chunks: List[str]) -> List[Dict[str, int]]:
        """Calculate start and end positions for each chunk in the original text"""
        positions = []
        start_pos = 0
        original_bytes = original_text.encode('utf-8')
        
        for chunk in chunks:
            chunk_bytes = chunk.encode('utf-8')
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
            
            # Calculate combined size in UTF-8 bytes
            combined_size = len((current_chunk + "\n" + chunk).encode('utf-8'))
            
            # Check if combining would exceed chunk_size
            if combined_size <= self.settings.chunk_size:
                current_chunk += "\n" + chunk
            else:
                # Add current chunk and start new one
                chunk_bytes = current_chunk.encode('utf-8')
                joined_chunks.append(ChunkInfo(
                    text=current_chunk,
                    size=len(chunk_bytes),
                    start_position=current_start,
                    end_position=positions[i-1]["end"]
                ))
                current_chunk = chunk
                current_start = positions[i]["start"]
        
        # Add the last chunk
        if current_chunk:
            chunk_bytes = current_chunk.encode('utf-8')
            joined_chunks.append(ChunkInfo(
                text=current_chunk,
                size=len(chunk_bytes),
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

        try:
            with time_limit(self.timeout_seconds):
                with memory_limit(self.max_memory_gb):
                    # Get appropriate splitter
                    splitter = self.splitters[splitter_type]
                    
                    # Split text
                    chunks = splitter.split_text(text)
                    
                    # Validate no empty chunks
                    chunks = [chunk for chunk in chunks if chunk.strip()]
                    if not chunks:
                        raise ValueError("Splitting resulted in no valid chunks")
                    
                    # Calculate positions
                    positions = self._get_chunk_positions(text, chunks)
                    
                    # Create chunk info objects
                    chunk_info_list = [
                        ChunkInfo(
                            text=chunk,
                            size=len(chunk.encode('utf-8')),
                            start_position=pos["start"],
                            end_position=pos["end"]
                        )
                        for chunk, pos in zip(chunks, positions)
                    ]
                    
                    # Join small chunks if requested
                    if join_chunks:
                        chunk_info_list = self._join_small_chunks(chunks, positions)
                    
                    # Validate chunk integrity
                    self.validate_chunk_integrity(text, chunk_info_list)
                    
                    return chunk_info_list

        except TimeoutError:
            logger.error(f"Processing timed out after {self.timeout_seconds} seconds")
            raise TimeoutError(f"Text processing timed out after {self.timeout_seconds} seconds")
        except MemoryError:
            logger.error(f"Exceeded memory limit of {self.max_memory_gb}GB")
            raise MemoryError(f"Process exceeded memory limit of {self.max_memory_gb}GB")
        except Exception as e:
            logger.error(f"Error processing text: {str(e)}")
            raise