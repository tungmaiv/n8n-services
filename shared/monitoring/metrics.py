# shared/monitoring/metrics.py
from prometheus_client import Counter, Histogram, Info, generate_latest
import time
from functools import wraps

class APIMetrics:
    def __init__(self, service_name: str):
        # Initialize metrics
        self.request_counter = Counter(
            'api_requests_total',
            'Total number of API requests',
            ['service', 'method', 'endpoint', 'status']
        )
        
        self.request_latency = Histogram(
            'api_request_latency_seconds',
            'Request latency in seconds',
            ['service', 'method', 'endpoint'],
            buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0)
        )
        
        self.info = Info('api_build_info', 'API build information')
        self.service_name = service_name

    def track_request(self, method: str, endpoint: str, status: int):
        """Track API request metrics"""
        self.request_counter.labels(
            service=self.service_name,
            method=method,
            endpoint=endpoint,
            status=status
        ).inc()

    def track_latency(self, method: str, endpoint: str, duration: float):
        """Track request latency"""
        self.request_latency.labels(
            service=self.service_name,
            method=method,
            endpoint=endpoint
        ).observe(duration)

    def set_build_info(self, version: str, commit: str):
        """Set build information"""
        self.info.info({
            'version': version,
            'commit': commit,
            'service': self.service_name
        })

def monitor_request(metrics: APIMetrics):
    """Decorator for monitoring FastAPI endpoints"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            method = "unknown"
            endpoint = "unknown"
            
            # Try to extract request information
            for arg in args:
                if hasattr(arg, 'method'):
                    method = arg.method
                if hasattr(arg, 'url'):
                    endpoint = str(arg.url.path)
            
            try:
                response = await func(*args, **kwargs)
                status = response.status_code
            except Exception as e:
                status = 500
                raise
            finally:
                duration = time.time() - start_time
                metrics.track_request(method, endpoint, status)
                metrics.track_latency(method, endpoint, duration)
            
            return response
        return wrapper
    return decorator