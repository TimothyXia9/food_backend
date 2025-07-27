#!/bin/bash

# Railway startup script for Django application
set -e

echo "Starting Django application..."

# Wait for database to be ready if DATABASE_URL is set
if [ -n "$DATABASE_URL" ]; then
    echo "Waiting for database to be ready..."
    
    # Simple database connection test
    python -c "
import os
import time
import django
from django.conf import settings

if not settings.configured:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'calorie_tracker.settings')
    django.setup()

from django.db import connection
from django.core.management.color import no_style

max_attempts = 30
attempt = 0

while attempt < max_attempts:
    try:
        connection.ensure_connection()
        print('Database connection successful!')
        break
    except Exception as e:
        attempt += 1
        print(f'Database connection attempt {attempt}/{max_attempts} failed: {e}')
        if attempt < max_attempts:
            time.sleep(2)
        else:
            print('Failed to connect to database after maximum attempts')
            exit(1)
"
fi

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Starting Gunicorn server..."
exec gunicorn \
    --bind 0.0.0.0:${PORT:-8000} \
    --workers 3 \
    --timeout 120 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --preload \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    calorie_tracker.wsgi:application