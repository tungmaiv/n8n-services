# shared/logging/logger.py
import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Optional
from elasticsearch import Elasticsearch
from .formatters import JSONFormatter

class ElasticsearchHandler(logging.Handler):
    """Handler for sending logs to Elasticsearch"""
    def __init__(self, host: str, index_prefix: str = "api-logs"):
        super().__init__()
        self.es_client = Elasticsearch(host)
        self.index_prefix = index_prefix

    def emit(self, record: logging.LogRecord):
        try:
            # Create log entry
            log_entry = {
                'timestamp': datetime.utcnow().isoformat(),
                'level': record.levelname,
                'service': record.service_name,
                'message': record.getMessage(),
                'logger': record.name
            }

            # Add extra fields if they exist
            if hasattr(record, 'extra'):
                log_entry.update(record.extra)

            # Create daily index
            index_name = f"{self.index_prefix}-{datetime.utcnow().strftime('%Y.%m.%d')}"
            
            # Send to Elasticsearch
            self.es_client.index(index=index_name, document=log_entry)
        except Exception as e:
            # Fallback to standard error logging
            print(f"Failed to send log to Elasticsearch: {e}")

class APILogger:
    """Main logger class for API applications"""
    def __init__(self, service_name: str, log_level: Optional[str] = None):
        self.service_name = service_name
        self.logger = logging.getLogger(service_name)
        self.logger.setLevel(log_level or os.getenv('LOG_LEVEL', 'INFO'))

        # Clear existing handlers
        self.logger.handlers = []

        # Add console handler with JSON formatting
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(JSONFormatter())
        self.logger.addHandler(console_handler)

        # Add file handler if LOG_FILE_PATH is set
        log_file = os.getenv('LOG_FILE_PATH')
        if log_file:
            file_handler = RotatingFileHandler(
                f"{log_file}/{service_name}.log",
                maxBytes=10485760,  # 10MB
                backupCount=5
            )
            file_handler.setFormatter(JSONFormatter())
            self.logger.addHandler(file_handler)

        # Add Elasticsearch handler if configured
        es_host = os.getenv('ELASTICSEARCH_HOST')
        if es_host:
            es_handler = ElasticsearchHandler(es_host)
            self.logger.addHandler(es_handler)

    def get_logger(self) -> logging.Logger:
        """Get the configured logger instance"""
        return self.logger

    def log_request(self, method: str, path: str, status_code: int, duration: float):
        """Log API request details"""
        self.logger.info(
            f"API Request: {method} {path}",
            extra={
                'method': method,
                'path': path,
                'status_code': status_code,
                'duration_seconds': duration,
                'service_name': self.service_name
            }
        )

    def log_error(self, error: Exception, context: dict = None):
        """Log error with context"""
        extra = {
            'error_type': type(error).__name__,
            'service_name': self.service_name
        }
        if context:
            extra.update(context)

        self.logger.error(
            str(error),
            extra=extra,
            exc_info=True
        )

# Example usage in an API:
'''
from shared.logging.logger import APILogger

# Initialize logger
logger = APILogger("api1").get_logger()

# Use in FastAPI endpoint
@app.get("/items/{item_id}")
async def read_item(item_id: int):
    logger.info(f"Fetching item {item_id}", extra={'item_id': item_id})
    try:
        # Your logic here
        pass
    except Exception as e:
        logger.error("Failed to fetch item", extra={'item_id': item_id})
        raise
'''