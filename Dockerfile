# Use Python 3.12 slim image for smaller size
FROM python:3.12.6-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=calorie_tracker.settings

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \
	&& apt-get install -y --no-install-recommends \
		build-essential \
		libpq-dev \
		libffi-dev \
		libssl-dev \
		curl \
	&& rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Create directories for logs and media
RUN mkdir -p logs media static

# Collect static files
RUN python manage.py collectstatic --noinput

# Create non-root user for security
RUN adduser --disabled-password --gecos '' appuser \
	&& chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Create entrypoint script for Railway PORT handling
RUN echo '#!/bin/bash\n\
# Set default port if PORT is not set\n\
PORT=${PORT:-8000}\n\
echo "Starting server on port: $PORT"\n\
\n\
# Run migrations\n\
python manage.py migrate --noinput\n\
\n\
# Collect static files\n\
python manage.py collectstatic --noinput\n\
\n\
# Start gunicorn with dynamic port\n\
exec gunicorn calorie_tracker.wsgi:application \\\n\
    --bind "0.0.0.0:${PORT}" \\\n\
    --workers 2 \\\n\
    --timeout 120 \\\n\
    --log-level info\n\
' > /app/entrypoint.sh && chmod +x /app/entrypoint.sh

# Health check with dynamic port
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
	CMD curl -f http://localhost:${PORT:-8000}/api/v1/health/ || exit 1

# Run the application using entrypoint script
CMD ["/app/entrypoint.sh"]