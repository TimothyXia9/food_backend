#!/usr/bin/env python3
"""
Debug script to check different food types for nutrient availability
"""

import os
import sys
import django
from django.conf import settings

# Add the project root to the Python path
sys.path.append('/home/tim/food_calorie/backend')

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'calorie_tracker.settings')
django.setup()

from foods.usda_service import get_usda_service

def debug_different_foods():
	"""Debug different food types for nutrient availability"""
	
	print("🔍 USDA Different Foods Debug")
	print("=" * 40)
	
	usda_service = get_usda_service()
	
	if not usda_service.is_available():
		print("USDA service not available")
		return
	
	# Test different food queries
	queries = ["apple", "chicken breast", "rice", "milk"]
	
	for query in queries:
		print(f"\n📝 Testing: {query}")
		print("-" * 30)
		
		search_result = usda_service.search_foods(query, page_size=3)
		
		if search_result['success']:
			foods = search_result.get('foods', [])
			
			for i, food in enumerate(foods):
				print(f"  {i+1}. {food.get('description')} (Type: {food.get('dataType')})")
				
				# Check for energy in this food
				nutrients = food.get('foodNutrients', [])
				energy_nutrients = [n for n in nutrients if n.get('nutrientId') == 1008]
				
				if energy_nutrients:
					energy_value = energy_nutrients[0].get('value', 0)
					print(f"     ✅ Energy: {energy_value} kcal")
				else:
					print(f"     ❌ No energy data")
				
				# Test extraction
				nutrition = usda_service._extract_nutrition_from_search_result(food)
				calories = nutrition.get('calories_per_100g', 0)
				print(f"     Extracted calories: {calories}")
				
				# Show first few nutrients
				nutrient_ids = [n.get('nutrientId') for n in nutrients[:5]]
				print(f"     First 5 nutrient IDs: {nutrient_ids}")
		else:
			print(f"   Search failed: {search_result.get('error')}")

if __name__ == "__main__":
	debug_different_foods()