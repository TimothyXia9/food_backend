from django.db import models
from django.conf import settings
import os


def upload_to_user_images(instance, filename):
    """Generate upload path for user images"""
    return f"user_{instance.user.id}/images/{filename}"


class UploadedImage(models.Model):
    """Images uploaded by users for food recognition"""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="uploaded_images",
    )
    meal = models.ForeignKey(
        "meals.Meal",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="images",
    )
    filename = models.CharField(max_length=255)
    file_path = models.ImageField(upload_to=upload_to_user_images, max_length=500)
    file_size = models.IntegerField(help_text="File size in bytes")
    mime_type = models.CharField(max_length=100)
    width = models.IntegerField(null=True, blank=True)
    height = models.IntegerField(null=True, blank=True)
    processing_status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="pending"
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-uploaded_at"]
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["processing_status"]),
        ]

    def __str__(self):
        return f"{self.filename} - {self.user.username}"

    def delete(self, *args, **kwargs):
        """Delete the image file when the model instance is deleted"""
        if self.file_path and os.path.isfile(self.file_path.path):
            os.remove(self.file_path.path)
        super().delete(*args, **kwargs)


class FoodRecognitionResult(models.Model):
    """Results from food recognition processing"""

    image = models.ForeignKey(
        UploadedImage, on_delete=models.CASCADE, related_name="recognition_results"
    )
    food = models.ForeignKey(
        "foods.Food", on_delete=models.SET_NULL, null=True, blank=True
    )
    confidence_score = models.DecimalField(
        max_digits=5, decimal_places=4, help_text="Recognition confidence (0-1)"
    )
    estimated_quantity = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Estimated quantity in grams",
    )
    is_confirmed = models.BooleanField(
        default=False, help_text="User confirmation status"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-confidence_score"]
        indexes = [
            models.Index(fields=["image"]),
        ]

    def __str__(self):
        food_name = self.food.name if self.food else "Unknown"
        return f"{food_name} ({self.confidence_score}) - {self.image.filename}"
