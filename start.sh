#!/bin/bash

# Exit on any error
set -e

echo "Starting Django application..."

# Set default port if PORT is not set
PORT=${PORT:-8000}
echo "Using port: $PORT"

# Run database migrations
echo "Running database migrations..."
python manage.py migrate --noinput

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Create media directory if it doesn't exist
mkdir -p /tmp/media

# Start the application
echo "Starting Gunicorn server on port $PORT..."
exec gunicorn calorie_tracker.wsgi:application \
    --bind 0.0.0.0:$PORT \
    --workers 2 \
    --worker-class sync \
    --worker-connections 1000 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --timeout 120 \
    --keepalive 5 \
    --log-level info \
    --access-logfile - \
    --error-logfile -