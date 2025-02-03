# Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better cache usage
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Create log directory
RUN mkdir -p /app/logs && \
    # Create non-root user
    useradd -m -u 1000 apiuser && \
    chown -R apiuser:apiuser /app

# Switch to non-root user
USER apiuser

# Start script
COPY start.sh .
RUN chmod +x start.sh
CMD ["./start.sh"]