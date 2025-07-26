"""
Meal serializers for API responses
"""

from rest_framework import serializers
from .models import Meal, MealFood, DailySummary
from foods.models import Food


class MealFoodSerializer(serializers.ModelSerializer):
    """Serializer for meal food items"""

    food_name = serializers.CharField(source="food.name", read_only=True)
    food_calories_per_100g = serializers.DecimalField(
        source="food.calories_per_100g", max_digits=8, decimal_places=2, read_only=True
    )

    class Meta:
        model = MealFood
        fields = [
            "id",
            "food",
            "food_name",
            "quantity",
            "calories",
            "protein",
            "fat",
            "carbs",
            "food_calories_per_100g",
            "added_at",
        ]
        read_only_fields = ["id", "calories", "protein", "fat", "carbs", "added_at"]


class MealSerializer(serializers.ModelSerializer):
    """Serializer for meals"""

    meal_foods = MealFoodSerializer(many=True, read_only=True)
    total_calories = serializers.DecimalField(
        max_digits=8, decimal_places=2, read_only=True
    )
    total_protein = serializers.DecimalField(
        max_digits=8, decimal_places=2, read_only=True
    )
    total_fat = serializers.DecimalField(max_digits=8, decimal_places=2, read_only=True)
    total_carbs = serializers.DecimalField(
        max_digits=8, decimal_places=2, read_only=True
    )

    class Meta:
        model = Meal
        fields = [
            "id",
            "date",
            "meal_type",
            "name",
            "notes",
            "meal_foods",
            "total_calories",
            "total_protein",
            "total_fat",
            "total_carbs",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class CreateMealSerializer(serializers.Serializer):
    """Serializer for creating meals"""

    date = serializers.DateTimeField()
    meal_type = serializers.ChoiceField(choices=Meal.MEAL_TYPE_CHOICES)
    name = serializers.CharField(max_length=200, required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    foods = serializers.ListField(
        child=serializers.DictField(), required=False, allow_empty=True
    )

    def validate_foods(self, value):
        """Validate foods list"""
        for food_item in value:
            if "food_id" not in food_item:
                raise serializers.ValidationError(
                    "food_id is required for each food item"
                )
            if "quantity" not in food_item:
                raise serializers.ValidationError(
                    "quantity is required for each food item"
                )

            # Validate food exists, unless it's a USDA food (indicated by fdc_id)
            if food_item["food_id"] != -1:  # -1 is placeholder for USDA foods
                try:
                    Food.objects.get(id=food_item["food_id"])
                except Food.DoesNotExist:
                    raise serializers.ValidationError(
                        f"Food with id {food_item['food_id']} not found"
                    )
            else:
                # For USDA foods (food_id = -1), validate that fdc_id is provided
                if "fdc_id" not in food_item:
                    raise serializers.ValidationError(
                        "fdc_id is required for USDA foods (when food_id is -1)"
                    )

        return value


class AddFoodToMealSerializer(serializers.Serializer):
    """Serializer for adding food to a meal"""

    food_id = serializers.IntegerField()
    quantity = serializers.DecimalField(max_digits=8, decimal_places=2)

    def validate_food_id(self, value):
        """Validate food exists"""
        try:
            Food.objects.get(id=value)
        except Food.DoesNotExist:
            raise serializers.ValidationError("Food not found")
        return value


class UpdateMealFoodSerializer(serializers.Serializer):
    """Serializer for updating meal food quantity"""

    quantity = serializers.DecimalField(max_digits=8, decimal_places=2)


class DailySummarySerializer(serializers.ModelSerializer):
    """Serializer for daily nutrition summaries"""

    class Meta:
        model = DailySummary
        fields = [
            "id",
            "date",
            "total_calories",
            "total_protein",
            "total_fat",
            "total_carbs",
            "total_fiber",
            "weight_recorded",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class MealListSerializer(serializers.Serializer):
    """Serializer for meal list requests"""

    # Legacy date parameters (for backward compatibility)
    date = serializers.DateField(required=False)
    meal_type = serializers.ChoiceField(choices=Meal.MEAL_TYPE_CHOICES, required=False)
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)

    # New timezone-aware UTC datetime parameters
    start_datetime_utc = serializers.DateTimeField(required=False)
    end_datetime_utc = serializers.DateTimeField(required=False)
    user_timezone = serializers.CharField(max_length=50, required=False)

    # Pagination
    page = serializers.IntegerField(default=1, min_value=1)
    page_size = serializers.IntegerField(default=20, min_value=1, max_value=100)

    def validate(self, data):
        """Validate date/datetime parameters"""
        # If using UTC datetime parameters, validate the range
        if data.get("start_datetime_utc") and data.get("end_datetime_utc"):
            if data["end_datetime_utc"] < data["start_datetime_utc"]:
                raise serializers.ValidationError(
                    "end_datetime_utc must be after start_datetime_utc"
                )

        # If using legacy date parameters, validate the range
        if data.get("start_date") and data.get("end_date"):
            if data["end_date"] < data["start_date"]:
                raise serializers.ValidationError("end_date must be after start_date")

        return data


class NutritionStatsSerializer(serializers.Serializer):
    """Serializer for nutrition statistics"""

    start_date = serializers.DateField()
    end_date = serializers.DateField()

    def validate(self, data):
        """Validate date range"""
        if data["end_date"] < data["start_date"]:
            raise serializers.ValidationError("end_date must be after start_date")
        return data


class WeightRecordSerializer(serializers.Serializer):
    """Serializer for weight records"""

    date = serializers.DateField()
    weight = serializers.DecimalField(max_digits=5, decimal_places=2)


class MealPlanSerializer(serializers.Serializer):
    """Serializer for meal planning"""

    date = serializers.DateField()
    meals = serializers.ListField(child=serializers.DictField(), allow_empty=True)

    def validate_meals(self, value):
        """Validate meals structure"""
        valid_meal_types = [choice[0] for choice in Meal.MEAL_TYPE_CHOICES]

        for meal in value:
            if "meal_type" not in meal:
                raise serializers.ValidationError("meal_type is required for each meal")
            if meal["meal_type"] not in valid_meal_types:
                raise serializers.ValidationError(
                    f"Invalid meal_type: {meal['meal_type']}"
                )
            if "foods" not in meal:
                raise serializers.ValidationError(
                    "foods list is required for each meal"
                )

            # Validate foods in each meal
            for food_item in meal["foods"]:
                if "food_id" not in food_item:
                    raise serializers.ValidationError(
                        "food_id is required for each food item"
                    )
                if "quantity" not in food_item:
                    raise serializers.ValidationError(
                        "quantity is required for each food item"
                    )

        return value
