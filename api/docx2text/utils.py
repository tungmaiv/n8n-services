# api/docx2text/utils.py
import os
import string
from docx import Document
from typing import Tuple
from shared.logging.logger import setup_logger

# Initialize logger
logger = setup_logger("docx2text_utils")

def validate_file_size(file_size: int) -> Tuple[bool, str]:
    """Validate file size against MAX_FILE_SIZE_MB environment variable"""
    try:
        max_size_mb = os.getenv('MAX_FILE_SIZE_MB')
        if max_size_mb is None:
            logger.error("MAX_FILE_SIZE_MB environment variable is not set")
            raise ValueError("MAX_FILE_SIZE_MB environment variable is not set")
        max_size_mb = int(max_size_mb)
        max_size = max_size_mb * 1024 * 1024  # Convert to bytes
    except (TypeError, ValueError):
        logger.error("Invalid MAX_FILE_SIZE_MB configuration")
        raise ValueError("Invalid MAX_FILE_SIZE_MB configuration")
    if file_size > max_size:
        return False, f"File size exceeds {max_size // (1024 * 1024)}MB limit"
    return True, ""

def clean_text(text: str) -> str:
    """Clean extracted text by removing special characters and converting to lowercase"""
    text = text.lower()
    text = text.translate(str.maketrans("", "", string.punctuation))
    text = " ".join(text.split())
    return text

def extract_text_from_docx(file_path: str) -> str:
    """Extract plain text from docx file"""
    doc = Document(file_path)
    full_text = []
    for paragraph in doc.paragraphs:
        full_text.append(paragraph.text)
    return "\n".join(full_text)