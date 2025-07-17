#!/usr/bin/env python3
"""
Compare search results vs detailed API calls
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

def compare_search_vs_detail():
	"""Compare search results with detailed API calls"""
	
	print("🔍 Search vs Detail Comparison")
	print("=" * 40)
	
	usda_service = get_usda_service()
	
	if not usda_service.is_available():
		print("USDA service not available")
		return
	
	# Search for apple
	search_result = usda_service.search_foods("apple", page_size=1)
	
	if search_result['success']:
		foods = search_result.get('foods', [])
		if foods:
			first_food = foods[0]
			fdc_id = first_food.get('fdcId')
			
			print(f"Food: {first_food.get('description')}")
			print(f"FDC ID: {fdc_id}")
			
			# Check search result nutrition
			search_nutrition = usda_service._extract_nutrition_from_search_result(first_food)
			print(f"\n📊 Search Result Nutrition:")
			print(f"  Calories: {search_nutrition.get('calories_per_100g')}")
			print(f"  Protein: {search_nutrition.get('protein_per_100g')}")
			print(f"  Fat: {search_nutrition.get('fat_per_100g')}")
			print(f"  Carbs: {search_nutrition.get('carbs_per_100g')}")
			
			# Now get detailed nutrition
			detail_result = usda_service.get_food_details(fdc_id)
			
			if detail_result['success']:
				detail_nutrition = detail_result['nutrition_data']
				print(f"\n📊 Detailed Nutrition:")
				print(f"  Calories: {detail_nutrition.get('calories_per_100g')}")
				print(f"  Protein: {detail_nutrition.get('protein_per_100g')}")
				print(f"  Fat: {detail_nutrition.get('fat_per_100g')}")
				print(f"  Carbs: {detail_nutrition.get('carbs_per_100g')}")
				
				# Compare
				print(f"\n🔍 Comparison:")
				print(f"  Search calories: {search_nutrition.get('calories_per_100g')}")
				print(f"  Detail calories: {detail_nutrition.get('calories_per_100g')}")
				
				if search_nutrition.get('calories_per_100g') == 0 and detail_nutrition.get('calories_per_100g') > 0:
					print("  ✅ Detail API provides calories when search doesn't!")
				elif search_nutrition.get('calories_per_100g') > 0:
					print("  ✅ Search already has calories")
				else:
					print("  ❌ Neither has calories")
			else:
				print(f"Detail API failed: {detail_result.get('error')}")
		else:
			print("No foods found in search")
	else:
		print(f"Search failed: {search_result.get('error')}")

if __name__ == "__main__":
	compare_search_vs_detail()