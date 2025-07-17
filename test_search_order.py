#!/usr/bin/env python3
"""
Test search order and data types
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

def test_search_order():
	"""Test search order and data types"""
	
	print("🔍 Search Order and Data Types Test")
	print("=" * 40)
	
	usda_service = get_usda_service()
	
	if not usda_service.is_available():
		print("USDA service not available")
		return
	
	result = usda_service.search_foods('apple', page_size=10)
	
	if result['success']:
		foods = result.get('foods', [])
		print(f'Found {len(foods)} foods')
		
		for i, food in enumerate(foods):
			data_type = food.get('dataType')
			description = food.get('description')
			
			# Check for energy
			nutrients = food.get('foodNutrients', [])
			energy_nutrients = [n for n in nutrients if n.get('nutrientId') == 1008]
			energy_value = energy_nutrients[0].get('value', 0) if energy_nutrients else 0
			
			print(f'{i+1}. {description} (Type: {data_type}) - Energy: {energy_value}')
	else:
		print(f'Error: {result.get("error")}')

if __name__ == "__main__":
	test_search_order()