# API Implementation Guide

```
n8n-services/
│
├── .env                          # Centralized environment variables
├── Dockerfile                    # Single container configuration
├── docker-compose.yml           # For local development
├── requirements.txt             # Project dependencies
├── README.md                    # Project documentation
│
├── api/                         # API services
│   ├── db_clean/
│   │   ├── __init__.py
│   │   ├── main.py             # API implementation
│   │   └── utils.py            # Service-specific utilities
│   │
│   ├── text_splitter/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   └── utils.py
│   │
│   ├── text_segmentor/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   └── utils.py
│   │
│   └── docx2text/
│       ├── __init__.py
│       ├── main.py
│       └── utils.py
│
├── shared/                      # Shared components
│   ├── __init__.py
│   ├── logging/
│   │   ├── __init__.py
│   │   └── logger.py           # Centralized logging configuration
│   │
│   └── monitoring/
│       ├── __init__.py
│       └── metrics.py          # Prometheus metrics configuration
│
├── config/
│   ├── logging.conf            # Logging configuration
│   └── prometheus/
│       └── metrics.yml         # Prometheus metrics configuration
│
├── logs/                       # Log files directory (mounted volume)
│   ├── .gitkeep
│   └── README.md              # Log directory documentation
│
└── scripts/
    ├── start.sh               # Container startup script
    └── healthcheck.sh         # Container health check script
```

Key aspects of this structure:

1. **Root Level**
   - `.env`: Single configuration file for all environment variables
   - `Dockerfile`: Single container configuration
   - `docker-compose.yml`: For local development and testing

2. **API Structure**
   - Each API service is isolated in its own directory
   - Consistent structure across all APIs
   - Shared utilities per service

3. **Shared Components**
   - Centralized logging configuration
   - Prometheus metrics setup
   - Easy to add more shared components

4. **Configuration**
   - Separated logging and monitoring configs
   - Easy to modify without changing code

5. **Logs**
   - Dedicated directory for logs
   - Mounted as a volume in Docker
   - Preserved between container restarts

6. **Scripts**
   - Container management scripts
   - Health monitoring

Example `.env` structure:
```env
# API Configurations
DB_CLEAN_PORT=3001
TEXT_CHUNKING_PORT=3002
TEXT_SEGMENTATION_PORT=3003
DOCX2TEXT_PORT=3004

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_DIR=/app/logs

# Monitoring
PROMETHEUS_PUSHGATEWAY=http://prometheus:9091
METRICS_PORT=9090

# Other Configurations
MAX_WORKERS=4
TIMEOUT=30
```

Example `Dockerfile`:
```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create log directory
RUN mkdir -p /app/logs

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD ./scripts/healthcheck.sh

# Start script
CMD ["./scripts/start.sh"]
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