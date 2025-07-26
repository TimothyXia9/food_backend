from django.db import models
from django.conf import settings
from decimal import Decimal


class Meal(models.Model):
    """Meals tracking user's food intake"""

    MEAL_TYPE_CHOICES = [
        ("breakfast", "Breakfast"),
        ("lunch", "Lunch"),
        ("dinner", "Dinner"),
        ("snack", "Snack"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="meals"
    )
    date = models.DateTimeField()  # 改为存储完整的UTC时间
    meal_type = models.CharField(max_length=20, choices=MEAL_TYPE_CHOICES)
    name = models.CharField(max_length=200, null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "meal_type"]
        indexes = [
            models.Index(fields=["user", "date"]),
            models.Index(fields=["user", "meal_type"]),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.get_meal_type_display()} ({self.date})"

    @property
    def total_calories(self):
        """Calculate total calories for this meal"""
        return sum(food.calories for food in self.meal_foods.all())

    @property
    def total_protein(self):
        """Calculate total protein for this meal"""
        return sum(food.protein or 0 for food in self.meal_foods.all())

    @property
    def total_fat(self):
        """Calculate total fat for this meal"""
        return sum(food.fat or 0 for food in self.meal_foods.all())

    @property
    def total_carbs(self):
        """Calculate total carbs for this meal"""
        return sum(food.carbs or 0 for food in self.meal_foods.all())


class MealFood(models.Model):
    """Individual food items within a meal"""

    meal = models.ForeignKey(Meal, on_delete=models.CASCADE, related_name="meal_foods")
    food = models.ForeignKey("foods.Food", on_delete=models.CASCADE)
    quantity = models.DecimalField(
        max_digits=8, decimal_places=2, help_text="Quantity in grams"
    )
    calories = models.DecimalField(max_digits=8, decimal_places=2)
    protein = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    fat = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    carbs = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["meal"]),
        ]

    def __str__(self):
        return f"{self.food.name} ({self.quantity}g) in {self.meal}"

    def save(self, *args, **kwargs):
        """Auto-calculate nutritional values based on quantity"""
        if self.food_id:
            multiplier = self.quantity / 100  # Convert to per 100g ratio
            self.calories = Decimal(str(self.food.calories_per_100g)) * multiplier
            if self.food.protein_per_100g:
                self.protein = Decimal(str(self.food.protein_per_100g)) * multiplier
            if self.food.fat_per_100g:
                self.fat = Decimal(str(self.food.fat_per_100g)) * multiplier
            if self.food.carbs_per_100g:
                self.carbs = Decimal(str(self.food.carbs_per_100g)) * multiplier
        super().save(*args, **kwargs)


class DailySummary(models.Model):
    """Daily nutritional summary for users"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="daily_summaries",
    )
    date = models.DateField()
    total_calories = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    total_protein = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    total_fat = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    total_carbs = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    total_fiber = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    weight_recorded = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Weight recorded for the day",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["user", "date"]
        ordering = ["-date"]
        indexes = [
            models.Index(fields=["user", "date"]),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.date}"

    def update_from_meals(self):
        """Update summary from all meals for this day"""
        meals = Meal.objects.filter(user=self.user, date=self.date)

        self.total_calories = sum(meal.total_calories for meal in meals)
        self.total_protein = sum(meal.total_protein for meal in meals)
        self.total_fat = sum(meal.total_fat for meal in meals)
        self.total_carbs = sum(meal.total_carbs for meal in meals)

        # Calculate fiber from meal foods
        meal_foods = MealFood.objects.filter(meal__in=meals)
        self.total_fiber = sum(
            Decimal(str(mf.food.fiber_per_100g or 0)) * (mf.quantity / 100)
            for mf in meal_foods
        )

        self.save()
