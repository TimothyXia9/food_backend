from django.urls import path
from . import views

urlpatterns = [
	# Food search and management
	path('search/', views.search_foods, name='search_foods'),
	path('<int:food_id>/', views.get_food_details, name='get_food_details'),
	path('create/', views.create_custom_food, name='create_custom_food'),
	path('<int:food_id>/update/', views.update_food, name='update_food'),
	path('<int:food_id>/delete/', views.delete_food, name='delete_food'),
	
	# USDA integration
	path('usda/search/', views.search_usda_foods, name='search_usda_foods'),
	path('usda/nutrition/<str:fdc_id>/', views.get_usda_nutrition, name='get_usda_nutrition'),
	path('usda/create/', views.create_food_from_usda, name='create_food_from_usda'),
	
	# Search history
	path('search/history/', views.get_search_history, name='get_search_history'),
]