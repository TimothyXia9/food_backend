"""
WSGI config for calorie_tracker project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/wsgi/
"""

import os
import logging

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "calorie_tracker.settings")

# Set up early logging to capture Django startup
logging.basicConfig(
    level=logging.DEBUG,
    format="[%(levelname)s] %(asctime)s %(name)s %(process)d %(thread)d - %(message)s",
    force=True,
)

logger = logging.getLogger("startup")
logger.info("[WSGI] Starting Django WSGI application...")

try:
    application = get_wsgi_application()
    logger.info("[WSGI] Django WSGI application created successfully")
except Exception as e:
    logger.error(f"[WSGI] Failed to create Django WSGI application: {e}")
    raise

import warnings

warnings.filterwarnings(
    "ignore", category=UserWarning, module="rest_framework_simplejwt"
)

logger.info("[WSGI] WSGI setup completed")

import psutil
import os

try:
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    logger.info(f"[MEMORY] Final memory usage: {memory_info.rss / 1024 / 1024:.2f}MB")
except:
    pass
