# shared/monitoring/metrics.py
from prometheus_client import Counter, Histogram, generate_latest
from contextlib import contextmanager
import time
import threading

class APIMetrics:
    def __init__(self, service_name):
        # Initialize metrics with service label
        self.request_count = Counter(
            'api_requests_total',
            'Total API requests',
            ['service', 'endpoint', 'method', 'status']
        )
        
        self.response_time = Histogram(
            'api_response_time_seconds',
            'API response time in seconds',
            ['service', 'endpoint'],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0]
        )
        
        self.error_count = Counter(
            'api_errors_total',
            'Total API errors',
            ['service', 'endpoint', 'error_type']
        )
        
        self.service_name = service_name

    def track_request(self, endpoint, method, status):
        self.request_count.labels(
            service=self.service_name,
            endpoint=endpoint,
            method=method,
            status=status
        ).inc()

    def track_error(self, endpoint, error_type):
        self.error_count.labels(
            service=self.service_name,
            endpoint=endpoint,
            error_type=error_type
        ).inc()

    @contextmanager
    def track_time(self, endpoint):
        start_time = time.time()
        thread_id = threading.get_ident()
        try:
            yield
        finally:
            duration = time.time() - start_time
            self.response_time.labels(
                service=f"{self.service_name}_{thread_id}",
                endpoint=endpoint
            ).observe(duration)

    def get_metrics(self):
        return generate_latest()