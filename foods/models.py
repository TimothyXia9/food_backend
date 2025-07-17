from django.db import models
from django.conf import settings


class Food(models.Model):
	"""Food items with nutritional information"""
	name = models.CharField(max_length=200)
	brand = models.CharField(max_length=100, null=True, blank=True)
	barcode = models.CharField(max_length=50, null=True, blank=True)
	serving_size = models.DecimalField(max_digits=8, decimal_places=2, help_text="Default serving size in grams")
	calories_per_100g = models.DecimalField(max_digits=8, decimal_places=2)
	protein_per_100g = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
	fat_per_100g = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
	carbs_per_100g = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
	fiber_per_100g = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
	sugar_per_100g = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
	sodium_per_100g = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
	is_verified = models.BooleanField(default=False, help_text="Data verification status")
	created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_foods')
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)
	usda_fdc_id = models.CharField(max_length=20, null=True, blank=True, help_text="USDA FoodData Central ID")

	class Meta:
		ordering = ['name']
		indexes = [
			models.Index(fields=['name']),
			models.Index(fields=['created_by']),
			models.Index(fields=['usda_fdc_id']),
		]

	def __str__(self):
		return self.name

	@property
	def is_custom(self):
		"""Check if this is a custom food created by a user"""
		return self.created_by is not None


class FoodAlias(models.Model):
	"""Alternative names for foods to improve search"""
	food = models.ForeignKey(Food, on_delete=models.CASCADE, related_name='aliases')
	alias = models.CharField(max_length=200)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		verbose_name_plural = "Food Aliases"
		indexes = [
			models.Index(fields=['alias']),
		]

	def __str__(self):
		return f"{self.alias} -> {self.food.name}"


class FoodSearchLog(models.Model):
	"""Log of food searches for analytics"""
	SEARCH_TYPE_CHOICES = [
		('text', 'Text Search'),
		('image', 'Image Recognition'),
		('barcode', 'Barcode Scan'),
	]

	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='search_logs')
	search_query = models.CharField(max_length=500)
	results_count = models.IntegerField(default=0)
	search_type = models.CharField(max_length=20, choices=SEARCH_TYPE_CHOICES)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-created_at']
		indexes = [
			models.Index(fields=['user']),
			models.Index(fields=['search_type']),
			models.Index(fields=['created_at']),
		]

	def __str__(self):
		return f"{self.search_query} ({self.search_type})"
