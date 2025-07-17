#!/usr/bin/env python3
"""
Debug script to analyze USDA API integration issues
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
import requests

def test_usda_integration():
	"""Test USDA API integration step by step"""
	
	print("🔍 USDA API Integration Debug")
	print("=" * 50)
	
	# Test 1: Service availability
	print("\n1. Testing service availability:")
	usda_service = get_usda_service()
	print(f"   Service available: {usda_service.is_available()}")
	print(f"   API keys count: {len(usda_service.api_keys)}")
	
	if not usda_service.is_available():
		print("   ❌ USDA service not available - no API keys configured")
		return
	
	# Test 2: Search foods
	print("\n2. Testing food search:")
	search_result = usda_service.search_foods("apple", page_size=3)
	print(f"   Search success: {search_result['success']}")
	
	if search_result['success']:
		foods = search_result.get('foods', [])
		print(f"   Foods found: {len(foods)}")
		
		if foods:
			first_food = foods[0]
			print(f"   First food: {first_food.get('description')}")
			print(f"   FDC ID: {first_food.get('fdcId')}")
			print(f"   Data Type: {first_food.get('dataType')}")
			
			# Check if search result has nutrition data
			if 'foodNutrients' in first_food:
				nutrients = first_food['foodNutrients']
				print(f"   Search result has {len(nutrients)} nutrients")
				
				# Look for calories in search result
				energy_nutrient = None
				for nutrient in nutrients:
					if nutrient.get('nutrientId') == 1008:  # Energy
						energy_nutrient = nutrient
						break
				
				if energy_nutrient:
					print(f"   Energy in search result: {energy_nutrient.get('value', 0)} kcal")
				else:
					print("   ❌ No energy nutrient found in search result")
			else:
				print("   ❌ No nutrition data in search result")
			
			# Test 3: Get detailed nutrition
			print("\n3. Testing detailed nutrition:")
			fdc_id = first_food.get('fdcId')
			detail_result = usda_service.get_food_details(fdc_id)
			
			if detail_result['success']:
				nutrition_data = detail_result['nutrition_data']
				print(f"   Detail success: True")
				print(f"   Description: {nutrition_data.get('description')}")
				print(f"   FDC ID: {nutrition_data.get('fdc_id')}")
				
				# Check formatted nutrition data
				nutrients = nutrition_data.get('nutrients', {})
				print(f"   Formatted nutrients: {list(nutrients.keys())}")
				
				# Check specific nutrients
				calories = nutrients.get('calories', {})
				protein = nutrients.get('protein', {})
				fat = nutrients.get('fat', {})
				carbs = nutrients.get('carbs', {})
				
				print(f"   Calories: {calories.get('amount', 0)} {calories.get('unit', 'N/A')}")
				print(f"   Protein: {protein.get('amount', 0)} {protein.get('unit', 'N/A')}")
				print(f"   Fat: {fat.get('amount', 0)} {fat.get('unit', 'N/A')}")
				print(f"   Carbs: {carbs.get('amount', 0)} {carbs.get('unit', 'N/A')}")
				
				# Test 4: Check the mapping to our API format
				print("\n4. Testing API format mapping:")
				
				# This is what the view expects
				expected_keys = [
					'calories_per_100g', 'protein_per_100g', 'fat_per_100g', 
					'carbs_per_100g', 'fiber_per_100g', 'sugar_per_100g', 'sodium_per_100g'
				]
				
				print("   Expected keys in nutrition_data:")
				for key in expected_keys:
					value = nutrition_data.get(key, 'MISSING')
					print(f"     {key}: {value}")
				
			else:
				print(f"   Detail failed: {detail_result.get('error')}")
	else:
		print(f"   Search failed: {search_result.get('error')}")
	
	# Test 5: Check the _format_nutrition_info function
	print("\n5. Testing direct API call:")
	try:
		url = "https://api.nal.usda.gov/fdc/v1/food/454004"
		params = {"api_key": "DEMO_KEY"}
		response = requests.get(url, params=params, timeout=10)
		
		if response.status_code == 200:
			raw_data = response.json()
			print(f"   Raw API call success: True")
			print(f"   Raw description: {raw_data.get('description')}")
			
			# Test our formatting function
			formatted = usda_service._format_nutrition_info(raw_data)
			print(f"   Formatted data keys: {list(formatted.keys())}")
			
			nutrients = formatted.get('nutrients', {})
			print(f"   Formatted nutrients: {list(nutrients.keys())}")
			
			if 'calories' in nutrients:
				calories = nutrients['calories']
				print(f"   Formatted calories: {calories.get('amount')} {calories.get('unit')}")
			else:
				print("   ❌ No calories in formatted data")
				
		else:
			print(f"   Raw API call failed: {response.status_code}")
			
	except Exception as e:
		print(f"   Raw API call error: {e}")

if __name__ == "__main__":
	test_usda_integration()