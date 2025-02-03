# API Implementation Guide

## Table of Contents
- [Project Structure](#project-structure)
- [Initial Setup](#initial-setup)
- [Core Components](#core-components)
- [API Generation](#api-generation)
- [Docker Configuration](#docker-configuration)
- [Implementation Best Practices](#implementation-best-practices)
- [Monitoring and Logging](#monitoring-and-logging)

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

### 1. Environment Setup

Create `.env.example`:
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

### 2. Dependencies

Create `requirements.txt`:
```txt
fastapi==0.104.1
uvicorn==0.24.0
gunicorn==21.2.0
prometheus-client==0.19.0
elasticsearch==8.11.0
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
            log_entry = {
                'timestamp': datetime.utcnow().isoformat(),
                'level': record.levelname,
                'service': record.service_name,
                'message': record.getMessage(),
                'logger': record.name
            }
            
            if hasattr(record, 'extra'):
                log_entry.update(record.extra)

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
                maxBytes=10485760,
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
        return self.logger
```

### 2. Formatter Implementation (shared/logging/formatters.py)

```python
import json
import logging
from datetime import datetime
import os

class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
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
    """Handles API metrics collection for Prometheus"""
    def __init__(self, service_name: str):
        self.service_name = service_name
        
        # Initialize metrics
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

    def track_request(self, method: str, endpoint: str, status_code: int):
        self.request_counter.labels(
            service=self.service_name,
            method=method,
            endpoint=endpoint,
            status=status_code
        ).inc()

def monitor_requests(metrics: APIMetrics):
    """Decorator for monitoring FastAPI endpoints"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = next((arg for arg in args if hasattr(arg, 'method')), None)
            if not request:
                return await func(*args, **kwargs)

            start_time = time.time()
            metrics.active_requests.labels(service=metrics.service_name).inc()

            try:
                response = await func(*args, **kwargs)
                status_code = response.status_code
                return response
            except Exception as e:
                metrics.track_error(type(e).__name__)
                status_code = 500
                raise
            finally:
                duration = time.time() - start_time
                endpoint = str(request.url.path)
                method = request.method
                
                metrics.track_request(method, endpoint, status_code)
                metrics.track_latency(method, endpoint, duration)
                metrics.active_requests.labels(service=metrics.service_name).dec()

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

2. Main API File (apis/new_api/main.py):
```python
from fastapi import FastAPI, Request
from shared.logging.logger import APILogger
from shared.monitoring.metrics import APIMetrics, monitor_requests
import os

app = FastAPI(
    title="New API",
    description="API Description",
    version="1.0.0"
)

logger = APILogger(os.getenv('SERVICE_NAME', 'new_api')).get_logger()
metrics = APIMetrics(os.getenv('SERVICE_NAME', 'new_api'))

@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(
        "Incoming request",
        extra={
            'method': request.method,
            'path': request.url.path
        }
    )
    response = await call_next(request)
    return response

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
```

3. Routes Template (apis/new_api/routes/v1/endpoints.py):
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
            "Error in example endpoint",
            extra={'error': str(e)}
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

### 1. Error Handling
```python
from fastapi import HTTPException
from typing import Dict, Any

async def handle_error(func) -> Dict[str, Any]:
    try:
        return await func()
    except Exception as e:
        logger.error(
            "Operation failed",
            extra={
                'error': str(e),
                'error_type': type(e).__name__
            }
        )
        raise HTTPException(status_code=500, detail=str(e))
```

### 2. Request Validation
```python
from pydantic import BaseModel, Field

class ItemBase(BaseModel):
    name: str = Field(..., description="Item name")
    description: str = Field(None, description="Item description")
```

### 3. Service Layer Pattern
```python
class BaseService:
    def __init__(self):
        self.logger = APILogger(self.__class__.__name__).get_logger()

    async def handle_operation(self, operation):
        try:
            return await operation()
        except Exception as e:
            self.logger.error(
                "Service operation failed",
                extra={'error': str(e)}
            )
            raise
```

## Monitoring and Logging

### 1. Prometheus Configuration
```yaml
scrape_configs:
  - job_name: 'api_metrics'
    scrape_interval: 15s
    static_configs:
      - targets: ['localhost:8080']
```

### 2. Logging Best Practices
- Use structured logging
- Include context in logs
- Use appropriate log levels
- Implement log rotation
- Monitor log volume

### 3. Metrics Best Practices
- Use meaningful metric names
- Add appropriate labels
- Monitor both technical and business metrics
- Set up alerting
- Watch cardinality

## Next Steps

1. Choose monitoring visualization tool (e.g., Grafana)
2. Set up alerting rules
3. Implement authentication/authorization
4. Add API documentation
5. Set up CI/CD pipeline