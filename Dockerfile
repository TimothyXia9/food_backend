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

# Collect static files (if needed at build time)
RUN python manage.py collectstatic --noinput || echo "Static collection skipped"

# Create entrypoint script BEFORE creating user
RUN echo '#!/bin/bash\n\
set -e\n\
\n\
# Use Railway PORT or default to 8000\n\
if [ -z "$PORT" ]; then\n\
    PORT=8000\n\
fi\n\
\n\
echo "Starting server on port: $PORT"\n\
\n\
# Run migrations\n\
echo "Running migrations..."\n\
python manage.py migrate --noinput\n\
\n\
# Collect static files at runtime\n\
echo "Collecting static files..."\n\
python manage.py collectstatic --noinput\n\
\n\
# Start gunicorn with the port\n\
echo "Starting gunicorn on 0.0.0.0:$PORT"\n\
exec gunicorn calorie_tracker.wsgi:application \\\n\
    --bind "0.0.0.0:$PORT" \\\n\
    --workers 2 \\\n\
    --timeout 120 \\\n\
    --log-level info \\\n\
    --access-logfile - \\\n\
    --error-logfile -\n\
' > /app/entrypoint.sh

# Make script executable
RUN chmod +x /app/entrypoint.sh

# Create non-root user for security
RUN adduser --disabled-password --gecos '' appuser \
    && chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Note: Railway handles port exposure automatically

# Run the application using entrypoint script
CMD ["/app/entrypoint.sh"]