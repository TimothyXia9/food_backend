#!/bin/bash

# Create necessary directories
mkdir -p staticfiles
mkdir -p media
mkdir -p logs

# Print startup information
echo "Starting Django application..."
echo "Python version: $(python --version)"
echo "Django version: $(python -c 'import django; print(django.get_version())')"
echo "Working directory: $(pwd)"
echo "Port: $PORT"

# Start gunicorn with proper logging
exec gunicorn calorie_tracker.wsgi:application \
    --bind 0.0.0.0:$PORT \
    --workers 1 \
    --timeout 300 \
    --log-level info \
    --access-logfile - \
    --error-logfile - \
    --capture-output