# shared/logging/logger.py
import logging
from logging.handlers import RotatingFileHandler
import os
from datetime import datetime

def setup_logger(service_name):
    """Setup logger with daily rotation and size limit"""
    logger = logging.getLogger(service_name)
    logger.setLevel(logging.INFO)

    # Create logs directory if it doesn't exist
    log_dir = os.getenv('LOG_DIR', '/app/logs')
    os.makedirs(log_dir, exist_ok=True)

    # Daily rotating file handler with size limit
    log_file = f"{log_dir}/{service_name}_{datetime.now().strftime('%Y-%m-%d')}.log"
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=1_000_000,  # 1MB
        backupCount=10
    )

    # Log format
    formatter = logging.Formatter(
        '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
        '"service": "%(name)s", "message": "%(message)s"}'
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger