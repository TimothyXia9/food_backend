from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
	"""Custom user model extending Django's AbstractUser"""
	email = models.EmailField(unique=True)
	nickname = models.CharField(max_length=50, blank=True)
	date_joined = models.DateTimeField(default=timezone.now)
	last_login = models.DateTimeField(null=True, blank=True)

	USERNAME_FIELD = 'username'
	REQUIRED_FIELDS = ['email']

	def __str__(self):
		return self.username


class UserProfile(models.Model):
	"""User profile with additional health and preference information"""
	GENDER_CHOICES = [
		('Male', 'Male'),
		('Female', 'Female'),
		('Other', 'Other'),
	]

	user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
	date_of_birth = models.DateField(null=True, blank=True)
	gender = models.CharField(max_length=10, choices=GENDER_CHOICES, null=True, blank=True)
	height = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Height in cm")
	weight = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Weight in kg")
	daily_calorie_goal = models.IntegerField(null=True, blank=True, help_text="Daily calorie target")
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	def __str__(self):
		return f"{self.user.username}'s Profile"


class UserActivityLog(models.Model):
	"""Log of user activities for analytics and debugging"""
	user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activity_logs')
	activity_type = models.CharField(max_length=50)
	activity_data = models.JSONField(null=True, blank=True)
	ip_address = models.GenericIPAddressField(null=True, blank=True)
	user_agent = models.CharField(max_length=500, null=True, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-created_at']
		indexes = [
			models.Index(fields=['user', 'activity_type']),
			models.Index(fields=['created_at']),
		]

	def __str__(self):
		return f"{self.user.username} - {self.activity_type}"
