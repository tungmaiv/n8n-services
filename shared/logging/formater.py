# shared/logging/formatters.py
import json
import logging
from datetime import datetime
import os

class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_object = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'message': record.getMessage(),
            'logger': record.name,
            'environment': os.getenv('ENVIRONMENT', 'development')
        }

        # Add service name if available
        if hasattr(record, 'service_name'):
            log_object['service'] = record.service_name

        # Add extra fields if they exist
        if hasattr(record, 'extra'):
            log_object.update(record.extra)

        # Add exception info if present
        if record.exc_info:
            log_object['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': self.formatException(record.exc_info)
            }

        return json.dumps(log_object)

# Example usage:
'''
from shared.logging.formatters import JSONFormatter

# Create handler
handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())

# Add to logger
logger = logging.getLogger('my_api')
logger.addHandler(handler)
'''