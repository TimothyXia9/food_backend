# Use Python 3.12 slim image as base
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV DEBIAN_FRONTEND noninteractive
ENV RAILWAY_ENVIRONMENT=1
ENV LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH

# Install system dependencies including libzbar for barcode detection
RUN apt-get update && apt-get install -y \
    libzbar0 \
    libzbar-dev \
    zbar-tools \
    libpq-dev \
    gcc \
    g++ \
    pkg-config \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/* \
    && ldconfig

# Set work directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . /app/

# Make start script executable
RUN chmod +x /app/start.sh

# Create a non-root user
RUN adduser --disabled-password --gecos '' appuser && chown -R appuser /app
USER appuser

# Note: collectstatic moved to runtime CMD to avoid build-time database dependency issues

# Expose port
EXPOSE 8000

# Run the application using startup script
CMD ["./start.sh"]