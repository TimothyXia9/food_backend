"""
Image serializers for API responses
"""

from rest_framework import serializers
from .models import UploadedImage, FoodRecognitionResult
from foods.models import Food


class UploadedImageSerializer(serializers.ModelSerializer):
    """Serializer for uploaded images"""

    class Meta:
        model = UploadedImage
        fields = [
            "id",
            "filename",
            "file_size",
            "mime_type",
            "width",
            "height",
            "processing_status",
            "uploaded_at",
            "processed_at",
        ]
        read_only_fields = [
            "id",
            "file_size",
            "mime_type",
            "width",
            "height",
            "uploaded_at",
            "processed_at",
        ]


class ImageUploadSerializer(serializers.Serializer):
    """Serializer for image upload requests"""

    image = serializers.ImageField()
    meal_id = serializers.IntegerField(required=False)


class FoodRecognitionResultSerializer(serializers.ModelSerializer):
    """Serializer for food recognition results"""

    food_name = serializers.CharField(source="food.name", read_only=True)
    food_calories_per_100g = serializers.DecimalField(
        source="food.calories_per_100g", max_digits=8, decimal_places=2, read_only=True
    )
    food_protein_per_100g = serializers.DecimalField(
        source="food.protein_per_100g", max_digits=8, decimal_places=2, read_only=True
    )
    food_fat_per_100g = serializers.DecimalField(
        source="food.fat_per_100g", max_digits=8, decimal_places=2, read_only=True
    )
    food_carbs_per_100g = serializers.DecimalField(
        source="food.carbs_per_100g", max_digits=8, decimal_places=2, read_only=True
    )

    class Meta:
        model = FoodRecognitionResult
        fields = [
            "id",
            "food_name",
            "confidence_score",
            "estimated_quantity",
            "is_confirmed",
            "food_calories_per_100g",
            "food_protein_per_100g",
            "food_fat_per_100g",
            "food_carbs_per_100g",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class ImageAnalysisRequestSerializer(serializers.Serializer):
    """Serializer for image analysis requests"""

    image_id = serializers.IntegerField()


class ImageAnalysisResultSerializer(serializers.Serializer):
    """Serializer for image analysis results"""

    success = serializers.BooleanField()
    image_id = serializers.IntegerField()
    processing_status = serializers.CharField()
    results = FoodRecognitionResultSerializer(many=True)


class ConfirmFoodRecognitionSerializer(serializers.Serializer):
    """Serializer for confirming food recognition results"""

    result_id = serializers.IntegerField()
    is_confirmed = serializers.BooleanField(default=True)


class CreateMealFromImageSerializer(serializers.Serializer):
    """Serializer for creating meals from image recognition"""

    image_id = serializers.IntegerField()
    meal_type = serializers.ChoiceField(
        choices=[
            ("breakfast", "Breakfast"),
            ("lunch", "Lunch"),
            ("dinner", "Dinner"),
            ("snack", "Snack"),
        ],
        default="snack",
    )
    date = serializers.DateField(required=False)
    meal_name = serializers.CharField(max_length=200, required=False)


class MealCreatedFromImageSerializer(serializers.Serializer):
    """Serializer for meal creation results"""

    success = serializers.BooleanField()
    meal_id = serializers.IntegerField()
    total_calories = serializers.FloatField()
    foods_added = serializers.ListField(child=serializers.DictField())


class BarcodeDetectionRequestSerializer(serializers.Serializer):
    """Serializer for barcode detection requests"""

    image_id = serializers.IntegerField()


class BarcodeDetectionResultSerializer(serializers.Serializer):
    """Serializer for barcode detection results"""

    data = serializers.CharField()
    type = serializers.CharField()
    quality = serializers.IntegerField(required=False, allow_null=True)
    orientation = serializers.CharField(required=False, allow_null=True)
    rect = serializers.DictField()
    polygon = serializers.ListField(child=serializers.ListField(child=serializers.IntegerField()), required=False)
    is_food_barcode = serializers.BooleanField()
    formatted_data = serializers.CharField()


class USDABarcodeSearchSerializer(serializers.Serializer):
    """Serializer for USDA barcode search requests"""

    barcode = serializers.CharField(max_length=20)


class USDABarcodeResultSerializer(serializers.Serializer):
    """Serializer for USDA barcode search results"""

    fdc_id = serializers.IntegerField()
    description = serializers.CharField()
    data_type = serializers.CharField()
    brand_owner = serializers.CharField()
    ingredients = serializers.CharField()
    gtin_upc = serializers.CharField()
    serving_size = serializers.CharField()
    serving_size_unit = serializers.CharField()
