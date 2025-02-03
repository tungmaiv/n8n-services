# api/docx2text/main.py
import os
import tempfile
from fastapi import APIRouter, UploadFile, HTTPException, Request
from fastapi.responses import JSONResponse
from typing import Dict, Any
from shared.logging.logger import setup_logger
from shared.monitoring.metrics import APIMetrics
from .utils import validate_file_size, clean_text, extract_text_from_docx

router = APIRouter()
logger = setup_logger("docx2text")
metrics = APIMetrics("docx2text")

ALLOWED_MIME_TYPES = ["application/vnd.openxmlformats-officedocument.wordprocessingml.document"]

@router.post("/convert")
async def convert_docx_to_text(request: Request, file: UploadFile) -> Dict[str, Any]:
    """Convert DOCX file to clean text"""
    logger.info(f"Processing file: {file.filename}")

    with metrics.track_time("/convert"):
        try:
            # Validate content type
            if file.content_type not in ALLOWED_MIME_TYPES:
                logger.error(f"Invalid content type: {file.content_type}")
                metrics.track_error("/convert", "InvalidContentType")
                raise HTTPException(status_code=400, detail="Invalid file type")

            # Read file content
            content = await file.read()
            
            # Validate file size
            is_valid, error_message = validate_file_size(len(content))
            if not is_valid:
                logger.error(f"File size validation failed: {error_message}")
                metrics.track_error("/convert", "FileSizeExceeded")
                raise HTTPException(status_code=400, detail=error_message)

            # Process file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.docx') as temp_file:
                temp_file.write(content)
                temp_path = temp_file.name

                try:
                    extracted_text = extract_text_from_docx(temp_path)
                    cleaned_text = clean_text(extracted_text)
                    
                    # Track successful conversion
                    metrics.track_request("/convert", request.method, 200)
                    logger.info(f"Successfully processed file: {file.filename}")
                    
                    return {"text": cleaned_text}
                finally:
                    os.unlink(temp_path)

        except Exception as e:
            logger.error(f"Error processing file: {str(e)}", exc_info=True)
            metrics.track_error("/convert", type(e).__name__)
            raise HTTPException(status_code=500, detail=str(e))