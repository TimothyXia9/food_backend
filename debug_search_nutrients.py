#!/usr/bin/env python3
"""
Debug script to check nutrient IDs in search results
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

def debug_search_nutrients():
	"""Debug the nutrient structure in search results"""
	
	print("🔍 USDA Search Nutrients Debug")
	print("=" * 40)
	
	usda_service = get_usda_service()
	
	if not usda_service.is_available():
		print("USDA service not available")
		return
	
	# Search for a food
	search_result = usda_service.search_foods("apple", page_size=1)
	
	if search_result['success']:
		foods = search_result.get('foods', [])
		if foods:
			first_food = foods[0]
			print(f"Food: {first_food.get('description')}")
			print(f"FDC ID: {first_food.get('fdcId')}")
			
			# Check nutrients in search result
			nutrients = first_food.get('foodNutrients', [])
			print(f"Nutrients found: {len(nutrients)}")
			
			# Print first few nutrients to see structure
			print("\nFirst 10 nutrients:")
			for i, nutrient in enumerate(nutrients[:10]):
				print(f"  {i+1}. ID: {nutrient.get('nutrientId')}, Name: {nutrient.get('nutrientName')}, Value: {nutrient.get('value')}")
			
			# Look for energy specifically
			energy_nutrients = [n for n in nutrients if n.get('nutrientId') == 1008]
			print(f"\nEnergy nutrients (ID 1008): {len(energy_nutrients)}")
			for nutrient in energy_nutrients:
				print(f"  {nutrient}")
			
			# Test our extraction function
			print("\n📊 Testing extraction function:")
			nutrition = usda_service._extract_nutrition_from_search_result(first_food)
			print(f"Extracted nutrition: {nutrition}")
	else:
		print(f"Search failed: {search_result.get('error')}")

if __name__ == "__main__":
	debug_search_nutrients()