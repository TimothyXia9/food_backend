web: python manage.py setup_db && gunicorn calorie_tracker.wsgi:application --bind 0.0.0.0:$PORT
release: python manage.py collectstatic --noinput