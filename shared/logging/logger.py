# shared/logging/logger.py
import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Optional
from .formatters import JSONFormatter

class APILogger:
    """Main logger class for API applications"""
    def __init__(self, service_name: str, log_level: Optional[str] = None):
        self.service_name = service_name
        self.logger = logging.getLogger(service_name)
        self.logger.setLevel(log_level or os.getenv('LOG_LEVEL', 'INFO'))
        
        # Initialize handlers
        self._init_handlers()

    def _init_handlers(self):
        self.logger.handlers = []
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(JSONFormatter())
        self.logger.addHandler(console_handler)
        
        # File handler with rotation
        log_path = os.getenv('LOG_FILE_PATH')
        if log_path:
            os.makedirs(log_path, exist_ok=True)
            file_handler = RotatingFileHandler(
                filename=f"{log_path}/{self.service_name}.log",
                maxBytes=10485760,  # 10MB
                backupCount=5,
                encoding='utf-8'
            )
            file_handler.setFormatter(JSONFormatter())
            self.logger.addHandler(file_handler)

    def get_logger(self) -> logging.Logger:
        """Get the configured logger instance"""
        return self.logger

    def log_error(self, error: Exception, context: dict = {}):
        """Log error with context"""
        extra = {'service_name': self.service_name}
        if context:
            extra.update(context)

        self.logger.error(
            str(error),
            extra=extra,
            exc_info=True
        )

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

# Example usage:
'''
logger = APILogger("api1").get_logger()
logger.info("Processing request", extra={'request_id': '123'})
'''