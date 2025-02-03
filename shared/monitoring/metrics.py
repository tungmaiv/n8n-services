# shared/monitoring/metrics.py
from prometheus_client import Counter, Histogram, Gauge, Info
import time
from functools import wraps
from typing import Optional

class APIMetrics:
    """Handles API metrics collection for Prometheus"""
    def __init__(self, service_name: str):
        self.service_name = service_name
        
        # Request metrics
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
        
        # Error metrics
        self.error_counter = Counter(
            'api_errors_total',
            'Total number of API errors',
            ['service', 'error_type']
        )
        
        # Active requests gauge
        self.active_requests = Gauge(
            'api_active_requests',
            'Number of active requests',
            ['service']
        )
        
        # Build info
        self.build_info = Info(
            'api_build_info',
            'API build information'
        )

    def track_request(self, method: str, endpoint: str, status_code: int):
        """Track API request metrics"""
        self.request_counter.labels(
            service=self.service_name,
            method=method,
            endpoint=endpoint,
            status=status_code
        ).inc()

    def track_latency(self, method: str, endpoint: str, duration: float):
        """Track request latency"""
        self.request_latency.labels(
            service=self.service_name,
            method=method,
            endpoint=endpoint
        ).observe(duration)

    def track_error(self, error_type: str):
        """Track API errors"""
        self.error_counter.labels(
            service=self.service_name,
            error_type=error_type
        ).inc()

    def set_build_info(self, version: str, commit: str):
        """Set API build information"""
        self.build_info.info({
            'version': version,
            'commit': commit,
            'service': self.service_name
        })

def monitor_requests(metrics: APIMetrics):
    """Decorator for monitoring FastAPI endpoints"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request from args (FastAPI dependency injection)
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

# Example usage in FastAPI:
'''
from fastapi import FastAPI
from shared.monitoring.metrics import APIMetrics, monitor_requests

app = FastAPI()
metrics = APIMetrics("api1")

# Set build info
metrics.set_build_info("1.0.0", "abc123")

@app.get("/items/{item_id}")
@monitor_requests(metrics)
async def read_item(item_id: int):
    return {"item_id": item_id}
'''