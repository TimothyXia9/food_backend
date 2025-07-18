from django.urls import path
from . import views

urlpatterns = [
	# Meal management
	path('create/', views.create_meal, name='create_meal'),
	path('<int:meal_id>/', views.get_meal_details, name='get_meal_details'),
	path('<int:meal_id>/update/', views.update_meal, name='update_meal'),
	path('<int:meal_id>/delete/', views.delete_meal, name='delete_meal'),
	path('list/', views.get_user_meals, name='get_user_meals'),
	path('recent/', views.get_recent_meals, name='get_recent_meals'),
	
	# Meal food management
	path('<int:meal_id>/add-food/', views.add_food_to_meal, name='add_food_to_meal'),
	path('food/<int:meal_food_id>/update/', views.update_meal_food, name='update_meal_food'),
	path('food/<int:meal_food_id>/delete/', views.remove_food_from_meal, name='remove_food_from_meal'),
	
	# Meal planning
	path('plan/', views.create_meal_plan, name='create_meal_plan'),
	
	# Nutrition tracking
	path('daily-summary/', views.get_daily_summary, name='get_daily_summary'),
	path('nutrition-stats/', views.get_nutrition_stats, name='get_nutrition_stats'),
	path('record-weight/', views.record_weight, name='record_weight'),
	
	# Meal statistics
	path('statistics/', views.get_meal_statistics, name='get_meal_statistics'),
	path('comparison/', views.get_meal_comparison, name='get_meal_comparison'),
]