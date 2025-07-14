"""
Food Image Analysis Service
Integrates the two-stage food analyzer with Django models
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
from django.conf import settings
from django.core.files.storage import default_storage
from django.db import transaction
from decimal import Decimal

from .models import UploadedImage, FoodRecognitionResult
from foods.models import Food, FoodCategory, FoodSearchLog
from foods.services import FoodDataService
from meals.models import Meal, MealFood
from calorie_tracker.openai_service import get_openai_service

# Import the refactored two-stage analyzer
from calorie_tracker.two_stage_analyzer import TwoStageFoodAnalyzer

logger = logging.getLogger(__name__)


class FoodImageAnalysisService:
	"""Service for analyzing food images using the two-stage approach"""
	
	def __init__(self):
		self.food_data_service = FoodDataService()
		self.analyzer = None
		
	def _get_analyzer(self):
		"""Get or create analyzer instance"""
		if not self.analyzer:
			config_path = Path(__file__).parent.parent / 'testing' / 'config_two_stage.json'
			self.analyzer = TwoStageFoodAnalyzer(str(config_path))
		return self.analyzer
	
	async def analyze_image(self, image_id: int, user_id: int) -> Dict[str, Any]:
		"""
		Analyze a food image using two-stage analysis
		
		Args:
			image_id: ID of the uploaded image
			user_id: ID of the user who uploaded the image
			
		Returns:
			Dictionary containing analysis results
		"""
		try:
			# Get the image record
			image = UploadedImage.objects.get(id=image_id, user_id=user_id)
			
			# Update status to processing
			image.processing_status = 'processing'
			image.save()
			
			# Get analyzer and run analysis
			analyzer = self._get_analyzer()
			image_path = image.file_path.path
			
			# Run two-stage analysis
			result = await analyzer.analyze_food_image(image_path)
			
			if result['success']:
				# Process and save results
				await self._process_analysis_results(image, result)
				
				# Update image status
				image.processing_status = 'completed'
				image.save()
				
				return {
					'success': True,
					'image_id': image_id,
					'analysis_result': result,
					'foods_identified': len(result['foods_with_nutrition']),
					'total_calories': result['summary']['total_nutrition']['calories']
				}
			else:
				# Analysis failed
				image.processing_status = 'failed'
				image.save()
				
				return {
					'success': False,
					'error': result.get('error', 'Analysis failed'),
					'image_id': image_id
				}
				
		except UploadedImage.DoesNotExist:
			return {
				'success': False,
				'error': 'Image not found',
				'image_id': image_id
			}
		except Exception as e:
			logger.error(f"Image analysis failed: {str(e)}")
			
			# Update image status to failed
			try:
				image = UploadedImage.objects.get(id=image_id)
				image.processing_status = 'failed'
				image.save()
			except:
				pass
			
			return {
				'success': False,
				'error': str(e),
				'image_id': image_id
			}
	
	async def _process_analysis_results(self, image: UploadedImage, result: Dict[str, Any]):
		"""Process and save analysis results to database"""
		
		foods_with_nutrition = result['foods_with_nutrition']
		
		with transaction.atomic():
			# Clear existing results for this image
			FoodRecognitionResult.objects.filter(image=image).delete()
			
			# Process each identified food
			for food_data in foods_with_nutrition:
				combined_data = food_data.get('combined_data')
				if not combined_data:
					continue
				
				# Try to find or create food in database
				food_obj = await self._get_or_create_food(combined_data)
				
				# Create recognition result
				recognition_result = FoodRecognitionResult.objects.create(
					image=image,
					food=food_obj,
					confidence_score=Decimal(str(combined_data.get('confidence', 0.5))),
					estimated_quantity=Decimal(str(combined_data.get('estimated_weight_grams', 0)))
				)
				
				# Log the search
				FoodSearchLog.objects.create(
					user=image.user,
					search_query=combined_data.get('name', ''),
					results_count=1,
					search_type='image'
				)
	
	async def _get_or_create_food(self, food_data: Dict[str, Any]) -> Food:
		"""Get or create a food record based on analysis data"""
		
		food_name = food_data.get('name', '')
		usda_match = food_data.get('usda_match', {})
		nutrition_per_portion = food_data.get('nutrition_per_portion', {})
		
		# Try to find existing food by name
		try:
			food = Food.objects.get(name__iexact=food_name)
			return food
		except Food.DoesNotExist:
			pass
		
		# Create new food record
		# Calculate nutrition per 100g from portion data
		estimated_weight = food_data.get('estimated_weight_grams', 100)
		multiplier = 100.0 / estimated_weight if estimated_weight > 0 else 1.0
		
		nutrition_per_100g = {}
		for key, value in nutrition_per_portion.items():
			if value:
				nutrition_per_100g[key] = value * multiplier
		
		# Get or create category
		category = None
		try:
			category, _ = FoodCategory.objects.get_or_create(
				name='Recognized Foods',
				defaults={'description': 'Foods identified from image recognition'}
			)
		except:
			pass
		
		# Create food record
		food = Food.objects.create(
			name=food_name,
			category=category,
			serving_size=Decimal('100.00'),
			calories_per_100g=Decimal(str(nutrition_per_100g.get('calories', 0))),
			protein_per_100g=Decimal(str(nutrition_per_100g.get('protein_g', 0))),
			fat_per_100g=Decimal(str(nutrition_per_100g.get('fat_g', 0))),
			carbs_per_100g=Decimal(str(nutrition_per_100g.get('carbs_g', 0))),
			fiber_per_100g=Decimal(str(nutrition_per_100g.get('fiber_g', 0))),
			is_verified=True  # From USDA data
		)
		
		return food
	
	def create_meal_from_image(self, image_id: int, user_id: int, meal_type: str = 'snack', date: str = None) -> Dict[str, Any]:
		"""Create a meal from recognized foods in an image"""
		
		try:
			# Get image and recognition results
			image = UploadedImage.objects.get(id=image_id, user_id=user_id)
			recognition_results = FoodRecognitionResult.objects.filter(
				image=image,
				is_confirmed=True
			)
			
			if not recognition_results.exists():
				return {
					'success': False,
					'error': 'No confirmed food items found'
				}
			
			# Create meal
			from datetime import datetime
			meal_date = datetime.strptime(date, '%Y-%m-%d').date() if date else datetime.now().date()
			
			meal = Meal.objects.create(
				user_id=user_id,
				date=meal_date,
				meal_type=meal_type,
				name=f"Meal from {image.filename}"
			)
			
			# Add foods to meal
			total_calories = 0
			foods_added = []
			
			for result in recognition_results:
				meal_food = MealFood.objects.create(
					meal=meal,
					food=result.food,
					quantity=result.estimated_quantity
				)
				
				foods_added.append({
					'food_name': result.food.name,
					'quantity': float(result.estimated_quantity),
					'calories': float(meal_food.calories)
				})
				
				total_calories += float(meal_food.calories)
			
			# Update image reference
			image.meal = meal
			image.save()
			
			return {
				'success': True,
				'meal_id': meal.id,
				'total_calories': total_calories,
				'foods_added': foods_added
			}
			
		except UploadedImage.DoesNotExist:
			return {
				'success': False,
				'error': 'Image not found'
			}
		except Exception as e:
			logger.error(f"Meal creation failed: {str(e)}")
			return {
				'success': False,
				'error': str(e)
			}
	
	def get_image_analysis_results(self, image_id: int, user_id: int) -> Dict[str, Any]:
		"""Get analysis results for an image"""
		
		try:
			image = UploadedImage.objects.get(id=image_id, user_id=user_id)
			recognition_results = FoodRecognitionResult.objects.filter(image=image)
			
			results = []
			for result in recognition_results:
				results.append({
					'id': result.id,
					'food_name': result.food.name if result.food else 'Unknown',
					'confidence_score': float(result.confidence_score),
					'estimated_quantity': float(result.estimated_quantity),
					'is_confirmed': result.is_confirmed,
					'nutrition': {
						'calories': float(result.food.calories_per_100g * result.estimated_quantity / 100) if result.food else 0,
						'protein': float(result.food.protein_per_100g * result.estimated_quantity / 100) if result.food and result.food.protein_per_100g else 0,
						'fat': float(result.food.fat_per_100g * result.estimated_quantity / 100) if result.food and result.food.fat_per_100g else 0,
						'carbs': float(result.food.carbs_per_100g * result.estimated_quantity / 100) if result.food and result.food.carbs_per_100g else 0,
					}
				})
			
			return {
				'success': True,
				'image_id': image_id,
				'processing_status': image.processing_status,
				'results': results
			}
			
		except UploadedImage.DoesNotExist:
			return {
				'success': False,
				'error': 'Image not found'
			}
		except Exception as e:
			logger.error(f"Failed to get analysis results: {str(e)}")
			return {
				'success': False,
				'error': str(e)
			}
	
	def confirm_food_recognition(self, result_id: int, user_id: int, is_confirmed: bool = True) -> Dict[str, Any]:
		"""Confirm or reject a food recognition result"""
		
		try:
			result = FoodRecognitionResult.objects.get(
				id=result_id,
				image__user_id=user_id
			)
			
			result.is_confirmed = is_confirmed
			result.save()
			
			return {
				'success': True,
				'result_id': result_id,
				'is_confirmed': is_confirmed
			}
			
		except FoodRecognitionResult.DoesNotExist:
			return {
				'success': False,
				'error': 'Recognition result not found'
			}
		except Exception as e:
			logger.error(f"Failed to confirm recognition: {str(e)}")
			return {
				'success': False,
				'error': str(e)
			}