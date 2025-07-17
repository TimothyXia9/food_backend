#!/usr/bin/env python3
"""
Final test of search results with updated service
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

def test_final_search():
	"""Final test of search results with updated service"""
	
	print("🔍 Final Search Test")
	print("=" * 40)
	
	usda_service = get_usda_service()
	
	if not usda_service.is_available():
		print("USDA service not available")
		return
	
	# Test different food queries
	queries = ["apple", "chicken", "rice", "milk", "beef"]
	
	for query in queries:
		print(f"\n📝 Testing: {query}")
		print("-" * 30)
		
		result = usda_service.search_foods(query, page_size=3)
		
		if result['success']:
			foods = result.get('foods', [])
			
			for i, food in enumerate(foods):
				description = food.get('description')
				data_type = food.get('dataType')
				
				# Test extraction
				nutrition = usda_service._extract_nutrition_from_search_result(food)
				calories = nutrition.get('calories_per_100g', 0)
				protein = nutrition.get('protein_per_100g', 0)
				
				status = "✅" if calories > 0 else "❌"
				print(f"  {i+1}. {description} (Type: {data_type})")
				print(f"     {status} Calories: {calories} kcal, Protein: {protein:.1f}g")
		else:
			print(f"   Search failed: {result.get('error')}")

if __name__ == "__main__":
	test_final_search()