# API Implementation Guide

## Table of Contents
- [Project Structure](#project-structure)
- [Initial Setup](#initial-setup)
- [Core Components Implementation](#core-components-implementation)
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

### Environment Configuration (.env.example)
```ini
# API Settings
API1_PORT=8000
API2_PORT=8001
METRICS_PORT=8080

# Logging
LOG_LEVEL=INFO
LOG_FILE_PATH=/app/logs
ELASTICSEARCH_HOST=http://elasticsearch:9200

# Environment
ENVIRONMENT=development
SERVICE_NAME=api1
```

### Dependencies (requirements.txt)
```txt
fastapi==0.104.1
uvicorn==0.24.0
gunicorn==21.2.0
prometheus-client==0.19.0
elasticsearch==8.11.0
python-dotenv==1.0.0
pydantic==2.5.2
```

## Core Components Implementation

### 1. Logging Implementation (shared/logging/logger.py)
```python
import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Optional
from elasticsearch import Elasticsearch
from .formatters import JSONFormatter

class ElasticsearchHandler(logging.Handler):
    def __init__(self, host: str, index_prefix: str = "api-logs"):
        super().__init__()
        self.es_client = Elasticsearch(host)
        self.index_prefix = index_prefix

    def emit(self, record: logging.LogRecord):
        try:
            log_entry = {
                'timestamp': datetime.utcnow().isoformat(),
                'level': record.levelname,
                'message': record.getMessage(),
                'logger': record.name,
                'environment': os.getenv('ENVIRONMENT', 'development')
            }
            
            if 'service_name' in record.__dict__:
                log_entry['service'] = record.__dict__['service_name']
            
            extras = {
                k: v for k, v in record.__dict__.items()
                if k not in {'args', 'asctime', 'created', 'exc_info', 'exc_text', 
                           'filename', 'funcName', 'levelname', 'levelno', 'lineno', 
                           'module', 'msecs', 'message', 'msg', 'name', 'pathname', 
                           'process', 'processName', 'relativeCreated', 'stack_info', 
                           'thread', 'threadName', 'service_name'}
            }
            log_entry.update(extras)

            if record.exc_info:
                log_entry['exception'] = {
                    'type': record.exc_info[0].__name__,
                    'message': str(record.exc_info[1]),
                    'traceback': self.formatter.formatException(record.exc_info)
                }

            index_name = f"{self.index_prefix}-{datetime.utcnow().strftime('%Y.%m.%d')}"
            self.es_client.index(index=index_name, document=log_entry)
        except Exception as e:
            print(f"Failed to send log to Elasticsearch: {e}")

class APILogger:
    def __init__(self, service_name: str, log_level: Optional[str] = None):
        self.service_name = service_name
        self.logger = logging.getLogger(service_name)
        self.logger.setLevel(log_level or os.getenv('LOG_LEVEL', 'INFO'))
        self._init_handlers()

    # ... [rest of the implementation remains the same]
```

### 2. JSON Formatter (shared/logging/formatters.py)
```python
import json
import logging
from datetime import datetime
import os

class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_object = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'message': record.getMessage(),
            'logger': record.name,
            'environment': os.getenv('ENVIRONMENT', 'development')
        }

        if hasattr(record, 'service_name'):
            log_object['service'] = record.service_name

        if hasattr(record, 'extra'):
            log_object.update(record.extra)

        if record.exc_info:
            log_object['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': self.formatException(record.exc_info)
            }

        return json.dumps(log_object)
```

### 3. Metrics Implementation (shared/monitoring/metrics.py)
```python
from prometheus_client import Counter, Histogram, Gauge, Info
import time
from functools import wraps

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
        self.active_requests = Gauge(
            'api_active_requests',
            'Number of active requests',
            ['service']
        )

    # ... [rest of the implementation remains the same]
```

## API Generation

### Template for New API

1. Create directory structure:
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
    
    logger.info(
        "Incoming request",
        extra={
            'method': request.method,
            'path': request.url.path,
            'client_ip': request.client.host
        }
    )
    
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

3. Example Route Implementation (apis/new_api/routes/v1/endpoints.py):
```python
from fastapi import APIRouter, HTTPException
from shared.monitoring.metrics import monitor_requests
from typing import Dict, Any

router = APIRouter(prefix="/v1")

@router.get("/example")
@monitor_requests(metrics)
async def example_endpoint() -> Dict[str, Any]:
    try:
        logger.info("Processing example request")
        return {"message": "success"}
    except Exception as e:
        logger.error(
            "Operation failed",
            extra={
                'operation': 'example_endpoint',
                'error': str(e)
            },
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Internal server error")
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
- Always include context in logs
- Use appropriate log levels
- Include request IDs for tracing
- Handle exceptions properly
- Use structured logging format

### 2. Metrics
- Use meaningful metric names
- Add appropriate labels
- Monitor both technical and business metrics
- Set up alerting rules
- Watch metric cardinality

### 3. Error Handling
- Use proper exception handling
- Include context in error logs
- Implement proper status codes
- Return meaningful error messages
- Maintain security in error responses

### 4. Code Organization
- Follow consistent project structure
- Implement service layer pattern
- Use proper type hints
- Maintain clean separation of concerns
- Document code properly

### 5. Security
- Implement proper authentication
- Use environment variables for configuration
- Run services as non-root user
- Implement rate limiting
- Handle sensitive data properly