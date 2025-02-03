# shared/logging/formatters.py
import json
import logging
from datetime import datetime
import os

class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    def format(self, record: logging.LogRecord) -> str:
        # Base log object with standard fields
        log_object = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'message': record.getMessage(),
            'logger': record.name,
            'environment': os.getenv('ENVIRONMENT', 'development')
        }

        # Add extra fields from record.__dict__
        extras = {
            k: v for k, v in record.__dict__.items()
            if k not in {
                'args', 'asctime', 'created', 'exc_info', 'exc_text', 
                'filename', 'funcName', 'levelname', 'levelno', 'lineno', 
                'module', 'msecs', 'message', 'msg', 'name', 'pathname', 
                'process', 'processName', 'relativeCreated', 'stack_info', 
                'thread', 'threadName'
            }
        }
        log_object.update(extras)

        # Add exception info if present
        if record.exc_info:
            try:
                log_object['exception'] = self.formatException(record.exc_info)
            except Exception:
                log_object['exception'] = 'Error formatting exception info'

        return json.dumps(log_object)