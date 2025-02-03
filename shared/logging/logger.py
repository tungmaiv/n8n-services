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
            # Base log entry
            log_entry = {
                'timestamp': datetime.utcnow().isoformat(),
                'level': record.levelname,
                'message': record.getMessage(),
                'logger': record.name,
                'environment': os.getenv('ENVIRONMENT', 'development')
            }
            
            # Add service name if available in record.__dict__
            if 'service_name' in record.__dict__:
                log_entry['service'] = record.__dict__['service_name']
            
            # Add any extra attributes from record.__dict__
            extras = {
                k: v for k, v in record.__dict__.items()
                if k not in {'args', 'asctime', 'created', 'exc_info', 'exc_text', 
                           'filename', 'funcName', 'levelname', 'levelno', 'lineno', 
                           'module', 'msecs', 'message', 'msg', 'name', 'pathname', 
                           'process', 'processName', 'relativeCreated', 'stack_info', 
                           'thread', 'threadName', 'service_name'}
            }
            log_entry.update(extras)

            # Add exception info if present
            if record.exc_info:
                log_entry['exception'] = {
                    'type': record.exc_info[0].__name__,
                    'message': str(record.exc_info[1]),
                    'traceback': self.formatter.formatException(record.exc_info)
                }

            # Create daily index
            index_name = f"{self.index_prefix}-{datetime.utcnow().strftime('%Y.%m.%d')}"
            self.es_client.index(index=index_name, document=log_entry)
        except Exception as e:
            print(f"Failed to send log to Elasticsearch: {e}")

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
        
        # File handler
        log_file = os.getenv('LOG_FILE_PATH')
        if log_file:
            file_handler = RotatingFileHandler(
                f"{log_file}/{self.service_name}.log",
                maxBytes=10485760,  # 10MB
                backupCount=5
            )
            file_handler.setFormatter(JSONFormatter())
            self.logger.addHandler(file_handler)
        
        # Elasticsearch handler
        es_host = os.getenv('ELASTICSEARCH_HOST')
        if es_host:
            es_handler = ElasticsearchHandler(es_host)
            self.logger.addHandler(es_handler)

    def get_logger(self) -> logging.Logger:
        """Get the configured logger instance"""
        return self.logger

    def log_error(self, error: Exception, context: dict = None):
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
logger.info("Test message", extra={'custom_field': 'value'})
'''