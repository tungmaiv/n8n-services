# API Implementation Guide

## Table of Contents
- [Project Structure](#project-structure)
- [Initial Setup](#initial-setup)
- [Core Components](#core-components)
- [API Generation](#api-generation)
- [Docker Configuration](#docker-configuration)
- [Implementation Best Practices](#implementation-best-practices)

## Project Structure
```
project_root/
├── README.md
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── start.sh
├── .env
├── .env.example
├── shared/
│   ├── __init__.py
│   ├── logging/
│   │   ├── __init__.py
│   │   ├── logger.py
│   │   └── formatters.py
│   └── monitoring/
│       ├── __init__.py
│       ├── metrics.py
│       └── prometheus_config.py
├── apis/
│   ├── __init__.py
│   ├── metrics/
│   │   ├── __init__.py
│   │   └── main.py
│   ├── api1/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   └── v1/
│   │   ├── models/
│   │   │   └── __init__.py
│   │   └── services/
│   │       └── __init__.py
│   └── api2/
│       └── [similar structure to api1]
└── tests/
    ├── __init__.py
    ├── conftest.py
    └── unit/
        └── __init__.py
```

## Initial Setup

### 1. Create Environment Files

**.env and .env.example:**
```ini
# API Settings
API1_PORT=8000
API2_PORT=8001
METRICS_PORT=8080

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE_PATH=/app/logs

# Environment Settings
ENVIRONMENT=development
SERVICE_NAME=api1

# Application Settings
DEBUG=False
ALLOWED_HOSTS=*

# Metrics Configuration
METRICS_PATH=/metrics
```

### 2. Dependencies (requirements.txt)
```txt
fastapi==0.104.1
uvicorn==0.24.0
gunicorn==21.2.0
prometheus-client==0.19.0
python-dotenv==1.0.0
pydantic==2.5.2
```

## Core Components

### 1. Logging Implementation (shared/logging/logger.py)
```python
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
```

### 2. JSON Formatter (shared/logging/formatters.py)
```python
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
```

### 3. Metrics Implementation (shared/monitoring/metrics.py)
```python
from prometheus_client import Counter, Histogram, Gauge
from functools import wraps
import time

class APIMetrics:
    def __init__(self, service_name: str):
        self.service_name = service_name
        
        self.request_counter = Counter(
            'api_requests_total',
            'Total number of API requests',
            ['service', 'method', 'endpoint', 'status']
        )
        
        self.request_latency = Histogram(
            'api_request_duration_seconds',
            'Request duration in seconds',
            ['service', 'method', 'endpoint'],
            buckets=(0.1, 0.5, 1.0, 2.0, 5.0)
        )
        
        self.error_counter = Counter(
            'api_errors_total',
            'Total number of API errors',
            ['service', 'error_type']
        )

def monitor_requests(metrics: APIMetrics):
    """Decorator for monitoring FastAPI endpoints"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = next((arg for arg in args if hasattr(arg, 'method')), None)
            start_time = time.time()

            try:
                response = await func(*args, **kwargs)
                duration = time.time() - start_time
                
                if request:
                    metrics.request_counter.labels(
                        service=metrics.service_name,
                        method=request.method,
                        endpoint=request.url.path,
                        status=response.status_code
                    ).inc()
                    
                    metrics.request_latency.labels(
                        service=metrics.service_name,
                        method=request.method,
                        endpoint=request.url.path
                    ).observe(duration)
                
                return response
            except Exception as e:
                metrics.error_counter.labels(
                    service=metrics.service_name,
                    error_type=type(e).__name__
                ).inc()
                raise

        return wrapper
    return decorator
```

## API Generation

### Template for New API

1. Create API Structure:
```bash
mkdir -p apis/new_api/{routes/v1,models,services}
touch apis/new_api/__init__.py
touch apis/new_api/main.py
touch apis/new_api/routes/v1/{__init__.py,endpoints.py}
touch apis/new_api/models/__init__.py
touch apis/new_api/services/__init__.py
```

2. Main API Implementation (apis/new_api/main.py):
```python
from fastapi import FastAPI, Request
from shared.logging.logger import APILogger
from shared.monitoring.metrics import APIMetrics, monitor_requests
import os
from datetime import datetime

app = FastAPI(
    title="New API",
    description="API Description",
    version="1.0.0"
)

# Initialize services
logger = APILogger(os.getenv('SERVICE_NAME', 'new_api')).get_logger()
metrics = APIMetrics(os.getenv('SERVICE_NAME', 'new_api'))

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = datetime.utcnow()
    
    try:
        response = await call_next(request)
        duration = (datetime.utcnow() - start_time).total_seconds()
        
        logger.info(
            "Request completed",
            extra={
                'method': request.method,
                'path': request.url.path,
                'status_code': response.status_code,
                'duration_seconds': duration
            }
        )
        return response
    except Exception as e:
        logger.error(
            "Request failed",
            extra={
                'method': request.method,
                'path': request.url.path,
                'error': str(e)
            },
            exc_info=True
        )
        raise

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
```

## Docker Configuration

### Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/logs
RUN useradd -m apiuser && \
    chown -R apiuser:apiuser /app
USER apiuser

COPY start.sh .
RUN chmod +x start.sh
CMD ["./start.sh"]
```

### start.sh
```bash
#!/bin/bash
set -e

# Start API1
gunicorn apis.api1.main:app --bind 0.0.0.0:8000 --worker-class uvicorn.workers.UvicornWorker --workers 2 --daemon

# Start API2
gunicorn apis.api2.main:app --bind 0.0.0.0:8001 --worker-class uvicorn.workers.UvicornWorker --workers 2 --daemon

# Start metrics endpoint
gunicorn apis.metrics.main:app --bind 0.0.0.0:8080 --worker-class uvicorn.workers.UvicornWorker --workers 1
```

## Implementation Best Practices

### 1. Logging
- Use structured JSON logging
- Include relevant context in logs
- Implement log rotation
- Use appropriate log levels
- Include request tracking

### 2. Metrics
- Track request counts and latencies
- Monitor error rates
- Use meaningful metric names
- Add appropriate labels

### 3. Error Handling
- Always include error context
- Use proper status codes
- Implement error logging
- Return meaningful error messages

### 4. Code Organization
- Follow consistent project structure
- Keep services modular
- Implement middleware properly
- Use type hints

### 5. Security
- Run as non-root user
- Use environment variables
- Implement proper error handling
- Validate input data