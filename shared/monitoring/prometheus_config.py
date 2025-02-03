# shared/monitoring/prometheus_config.py
from typing import Dict, Any
import os

def get_prometheus_config() -> Dict[str, Any]:
    """Get Prometheus configuration settings"""
    return {
        'metrics_path': os.getenv('METRICS_PATH', '/metrics'),
        'buckets': (0.1, 0.5, 1.0, 2.0, 5.0),
        'quantiles': (0.5, 0.9, 0.95, 0.99),
        'labels': {
            'environment': os.getenv('ENVIRONMENT', 'development'),
            'region': os.getenv('REGION', 'default')
        }
    }

# Sample Prometheus scrape configuration (prometheus.yml)
'''
scrape_configs:
  - job_name: 'api_metrics'
    scrape_interval: 15s
    static_configs:
      - targets: ['localhost:8080']  # Metrics endpoint
    metrics_path: /metrics
'''

# Sample Grafana dashboard queries
'''
# Request Rate
rate(api_requests_total{service="api1"}[5m])

# Error Rate
rate(api_errors_total{service="api1"}[5m])

# 95th Percentile Latency
histogram_quantile(0.95, sum(rate(api_request_duration_seconds_bucket{service="api1"}[5m])) by (le))

# Active Requests
api_active_requests{service="api1"}
'''