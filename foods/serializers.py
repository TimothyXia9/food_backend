"""
Food serializers for API responses
"""

from rest_framework import serializers
from .models import Food, FoodAlias, FoodSearchLog


class FoodAliasSerializer(serializers.ModelSerializer):
    """Serializer for food aliases"""

    class Meta:
        model = FoodAlias
        fields = ["id", "alias", "created_at"]
        read_only_fields = ["id", "created_at"]


class FoodSerializer(serializers.ModelSerializer):
    """Serializer for food items"""

    aliases = FoodAliasSerializer(many=True, read_only=True)
    is_custom = serializers.BooleanField(read_only=True)

    class Meta:
        model = Food
        fields = [
            "id",
            "name",
            "brand",
            "barcode",
            "serving_size",
            "calories_per_100g",
            "protein_per_100g",
            "fat_per_100g",
            "carbs_per_100g",
            "fiber_per_100g",
            "sugar_per_100g",
            "sodium_per_100g",
            "is_verified",
            "is_custom",
            "aliases",
            "usda_fdc_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "is_verified", "created_at", "updated_at"]


class FoodSearchSerializer(serializers.Serializer):
    """Serializer for food search requests"""

    query = serializers.CharField(max_length=500)
    page = serializers.IntegerField(default=1, min_value=1)
    page_size = serializers.IntegerField(default=20, min_value=1, max_value=100)


class FoodSearchResultSerializer(serializers.Serializer):
    """Serializer for food search results"""

    id = serializers.IntegerField()
    name = serializers.CharField()
    brand = serializers.CharField(allow_null=True)
    serving_size = serializers.FloatField()
    calories_per_100g = serializers.FloatField()
    protein_per_100g = serializers.FloatField()
    fat_per_100g = serializers.FloatField()
    carbs_per_100g = serializers.FloatField()
    fiber_per_100g = serializers.FloatField()
    is_verified = serializers.BooleanField()
    is_custom = serializers.BooleanField()


class USDAFoodSearchSerializer(serializers.Serializer):
    """Serializer for USDA food search requests"""

    query = serializers.CharField(max_length=500)
    page_size = serializers.IntegerField(default=25, min_value=1, max_value=100)


class USDAFoodResultSerializer(serializers.Serializer):
    """Serializer for USDA food search results"""

    fdc_id = serializers.IntegerField()
    description = serializers.CharField()
    data_type = serializers.CharField()
    brand_owner = serializers.CharField(allow_blank=True)
    ingredients = serializers.CharField(allow_blank=True)


class USDANutritionSerializer(serializers.Serializer):
    """Serializer for USDA nutrition data"""

    fdc_id = serializers.IntegerField()


class CreateFoodFromUSDASerializer(serializers.Serializer):
    """Serializer for creating food from USDA data"""

    fdc_id = serializers.IntegerField()


class CustomFoodSerializer(serializers.Serializer):
    """Serializer for creating custom foods"""

    name = serializers.CharField(max_length=200)
    brand = serializers.CharField(
        max_length=100, required=False, allow_blank=True, default=""
    )
    barcode = serializers.CharField(
        max_length=50, required=False, allow_blank=True, default=""
    )
    serving_size = serializers.DecimalField(max_digits=8, decimal_places=2, default=100)
    calories_per_100g = serializers.DecimalField(max_digits=8, decimal_places=2)
    protein_per_100g = serializers.DecimalField(
        max_digits=8, decimal_places=2, default=0
    )
    fat_per_100g = serializers.DecimalField(max_digits=8, decimal_places=2, default=0)
    carbs_per_100g = serializers.DecimalField(max_digits=8, decimal_places=2, default=0)
    fiber_per_100g = serializers.DecimalField(max_digits=8, decimal_places=2, default=0)
    sugar_per_100g = serializers.DecimalField(max_digits=8, decimal_places=2, default=0)
    sodium_per_100g = serializers.DecimalField(
        max_digits=8, decimal_places=2, default=0
    )
    aliases = serializers.ListField(
        child=serializers.CharField(max_length=200), required=False, allow_empty=True
    )


class FoodSearchLogSerializer(serializers.ModelSerializer):
    """Serializer for food search logs"""

    class Meta:
        model = FoodSearchLog
        fields = ["id", "search_query", "results_count", "search_type", "created_at"]
        read_only_fields = ["id", "created_at"]
