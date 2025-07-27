from django.urls import path
from . import views

urlpatterns = [
    # Image upload and management
    path("upload/", views.upload_image, name="upload_image"),
    path("analyze/", views.analyze_image, name="analyze_image"),
    path(
        "analyze-stream/", views.analyze_image_streaming, name="analyze_image_streaming"
    ),
    path("<int:image_id>/results/", views.get_image_results, name="get_image_results"),
    path("<int:image_id>/delete/", views.delete_image, name="delete_image"),
    path("list/", views.get_user_images, name="get_user_images"),
    # Food recognition management
    path("confirm/", views.confirm_food_recognition, name="confirm_food_recognition"),
    path("create-meal/", views.create_meal_from_image, name="create_meal_from_image"),
    # Barcode detection endpoints
    path("detect-barcodes/", views.detect_barcodes, name="detect_barcodes"),
    path("search-usda-barcode/", views.search_usda_by_barcode, name="search_usda_by_barcode"),
    path("analyze-with-barcode/", views.analyze_image_with_barcode, name="analyze_image_with_barcode"),
]
