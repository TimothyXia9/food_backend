"""
URL configuration for calorie_tracker project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse


def health_check(request):
    """Health check endpoint for Railway"""
    import os
    import django
    from django.db import connection
    from django.conf import settings

    # Basic health status
    health_data = {
        "status": "healthy",
        "service": "calorie_tracker",
        "version": "1.0.0",
        "django_version": django.get_version(),
        "environment": os.environ.get("RAILWAY_ENVIRONMENT", "development"),
        "timestamp": "2025-01-24",
    }

    # Database connection test
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            health_data["database"] = "connected"
            health_data["database_engine"] = settings.DATABASES["default"]["ENGINE"]
    except Exception as e:
        health_data["database"] = f"error: {str(e)[:100]}"
        health_data["database_engine"] = settings.DATABASES["default"].get(
            "ENGINE", "unknown"
        )
        # Don't fail the health check just because DB is down
        # Railway needs the HTTP server to be responsive

    # Environment info for debugging
    if "RAILWAY_ENVIRONMENT" in os.environ:
        health_data["debug_info"] = {
            "has_database_url": "DATABASE_URL" in os.environ,
            "pg_host": os.environ.get("PGHOST", "not_set"),
            "pg_database": os.environ.get("PGDATABASE", "not_set"),
        }

    return JsonResponse(health_data)


def barcode_debug(request):
    """Quick barcode dependency debug"""
    debug_info = {"status": "checking"}
    
    try:
        # Test system library
        import ctypes
        ctypes.CDLL('libzbar.so.0')
        debug_info["libzbar"] = "OK"
    except Exception as e:
        debug_info["libzbar"] = f"ERROR: {str(e)}"
    
    try:
        # Test Python packages
        import cv2, numpy, PIL, pyzbar
        debug_info["python_packages"] = "OK"
        debug_info["cv2_version"] = cv2.__version__
        debug_info["numpy_version"] = numpy.__version__
    except Exception as e:
        debug_info["python_packages"] = f"ERROR: {str(e)}"
    
    try:
        # Test barcode service
        from images.barcode_service import BarcodeDetectionService
        service = BarcodeDetectionService()
        debug_info["barcode_service"] = service.dependencies_available
    except Exception as e:
        debug_info["barcode_service"] = f"ERROR: {str(e)}"
    
    return JsonResponse(debug_info)


urlpatterns = [
    path("", health_check),  # Root health check
    path("health/", health_check),  # Alternative health check
    path("api/v1/health/", health_check),
    path("barcode-debug/", barcode_debug),  # Quick debug
    path("admin/", admin.site.urls),
    path("api/v1/auth/", include("accounts.urls")),
    path("api/v1/users/", include("accounts.urls")),
    path("api/v1/foods/", include("foods.urls")),
    path("api/v1/meals/", include("meals.urls")),
    path("api/v1/images/", include("images.urls")),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
