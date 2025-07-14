"""
Meals service for managing meal tracking and nutrition summaries
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from django.db.models import Q, Sum, Count
from django.db import transaction
from django.core.paginator import Paginator
from decimal import Decimal

from .models import Meal, MealFood, DailySummary
from foods.models import Food

logger = logging.getLogger(__name__)


class MealsService:
	"""Service for managing meals and nutrition tracking"""
	
	def create_meal(self, user_id: int, meal_data: Dict[str, Any]) -> Dict[str, Any]:
		"""Create a new meal with foods"""
		
		try:
			with transaction.atomic():
				# Create meal
				meal = Meal.objects.create(
					user_id=user_id,
					date=meal_data['date'],
					meal_type=meal_data['meal_type'],
					name=meal_data.get('name', ''),
					notes=meal_data.get('notes', '')
				)
				
				# Add foods if provided
				foods_added = []
				if meal_data.get('foods'):
					for food_item in meal_data['foods']:
						food = Food.objects.get(id=food_item['food_id'])
						
						meal_food = MealFood.objects.create(
							meal=meal,
							food=food,
							quantity=Decimal(str(food_item['quantity']))
						)
						
						foods_added.append({
							'food_id': food.id,
							'food_name': food.name,
							'quantity': float(meal_food.quantity),
							'calories': float(meal_food.calories)
						})
				
				# Update daily summary
				self._update_daily_summary(user_id, meal_data['date'])
				
				return {
					'success': True,
					'meal_id': meal.id,
					'foods_added': foods_added,
					'total_calories': float(meal.total_calories),
					'message': 'Meal created successfully'
				}
				
		except Food.DoesNotExist:
			return {
				'success': False,
				'error': 'One or more foods not found'
			}
		except Exception as e:
			logger.error(f"Failed to create meal: {str(e)}")
			return {
				'success': False,
				'error': str(e)
			}
	
	def get_meal_details(self, meal_id: int, user_id: int) -> Dict[str, Any]:
		"""Get detailed information about a meal"""
		
		try:
			meal = Meal.objects.get(id=meal_id, user_id=user_id)
			
			# Get meal foods
			meal_foods = []
			for meal_food in meal.meal_foods.all():
				meal_foods.append({
					'id': meal_food.id,
					'food_id': meal_food.food.id,
					'food_name': meal_food.food.name,
					'quantity': float(meal_food.quantity),
					'calories': float(meal_food.calories),
					'protein': float(meal_food.protein or 0),
					'fat': float(meal_food.fat or 0),
					'carbs': float(meal_food.carbs or 0),
					'added_at': meal_food.added_at.isoformat()
				})
			
			return {
				'success': True,
				'meal': {
					'id': meal.id,
					'date': meal.date.isoformat(),
					'meal_type': meal.meal_type,
					'name': meal.name,
					'notes': meal.notes,
					'foods': meal_foods,
					'total_calories': float(meal.total_calories),
					'total_protein': float(meal.total_protein),
					'total_fat': float(meal.total_fat),
					'total_carbs': float(meal.total_carbs),
					'created_at': meal.created_at.isoformat(),
					'updated_at': meal.updated_at.isoformat()
				}
			}
			
		except Meal.DoesNotExist:
			return {
				'success': False,
				'error': 'Meal not found'
			}
		except Exception as e:
			logger.error(f"Failed to get meal details: {str(e)}")
			return {
				'success': False,
				'error': str(e)
			}
	
	def add_food_to_meal(self, meal_id: int, user_id: int, food_id: int, quantity: Decimal) -> Dict[str, Any]:
		"""Add a food item to an existing meal"""
		
		try:
			with transaction.atomic():
				# Get meal and food
				meal = Meal.objects.get(id=meal_id, user_id=user_id)
				food = Food.objects.get(id=food_id)
				
				# Create meal food
				meal_food = MealFood.objects.create(
					meal=meal,
					food=food,
					quantity=quantity
				)
				
				# Update daily summary
				self._update_daily_summary(user_id, meal.date)
				
				return {
					'success': True,
					'meal_food_id': meal_food.id,
					'food_name': food.name,
					'quantity': float(quantity),
					'calories': float(meal_food.calories),
					'message': 'Food added to meal successfully'
				}
				
		except Meal.DoesNotExist:
			return {
				'success': False,
				'error': 'Meal not found'
			}
		except Food.DoesNotExist:
			return {
				'success': False,
				'error': 'Food not found'
			}
		except Exception as e:
			logger.error(f"Failed to add food to meal: {str(e)}")
			return {
				'success': False,
				'error': str(e)
			}
	
	def update_meal_food(self, meal_food_id: int, user_id: int, quantity: Decimal) -> Dict[str, Any]:
		"""Update the quantity of a food item in a meal"""
		
		try:
			with transaction.atomic():
				# Get meal food
				meal_food = MealFood.objects.get(
					id=meal_food_id,
					meal__user_id=user_id
				)
				
				# Update quantity
				meal_food.quantity = quantity
				meal_food.save()
				
				# Update daily summary
				self._update_daily_summary(user_id, meal_food.meal.date)
				
				return {
					'success': True,
					'meal_food_id': meal_food_id,
					'new_quantity': float(quantity),
					'new_calories': float(meal_food.calories),
					'message': 'Food quantity updated successfully'
				}
				
		except MealFood.DoesNotExist:
			return {
				'success': False,
				'error': 'Meal food not found'
			}
		except Exception as e:
			logger.error(f"Failed to update meal food: {str(e)}")
			return {
				'success': False,
				'error': str(e)
			}
	
	def remove_food_from_meal(self, meal_food_id: int, user_id: int) -> Dict[str, Any]:
		"""Remove a food item from a meal"""
		
		try:
			with transaction.atomic():
				# Get meal food
				meal_food = MealFood.objects.get(
					id=meal_food_id,
					meal__user_id=user_id
				)
				
				meal_date = meal_food.meal.date
				meal_food.delete()
				
				# Update daily summary
				self._update_daily_summary(user_id, meal_date)
				
				return {
					'success': True,
					'message': 'Food removed from meal successfully'
				}
				
		except MealFood.DoesNotExist:
			return {
				'success': False,
				'error': 'Meal food not found'
			}
		except Exception as e:
			logger.error(f"Failed to remove food from meal: {str(e)}")
			return {
				'success': False,
				'error': str(e)
			}
	
	def get_user_meals(self, user_id: int, filters: Dict[str, Any]) -> Dict[str, Any]:
		"""Get user's meals with optional filtering"""
		
		try:
			# Build query
			query = Q(user_id=user_id)
			
			# Apply filters
			if filters.get('date'):
				query &= Q(date=filters['date'])
			if filters.get('meal_type'):
				query &= Q(meal_type=filters['meal_type'])
			if filters.get('start_date'):
				query &= Q(date__gte=filters['start_date'])
			if filters.get('end_date'):
				query &= Q(date__lte=filters['end_date'])
			
			# Get meals
			meals = Meal.objects.filter(query).order_by('-date', 'meal_type')
			
			# Paginate
			page = filters.get('page', 1)
			page_size = filters.get('page_size', 20)
			
			paginator = Paginator(meals, page_size)
			page_obj = paginator.get_page(page)
			
			# Format results
			results = []
			for meal in page_obj.object_list:
				results.append({
					'id': meal.id,
					'date': meal.date.isoformat(),
					'meal_type': meal.meal_type,
					'name': meal.name,
					'total_calories': float(meal.total_calories),
					'total_protein': float(meal.total_protein),
					'total_fat': float(meal.total_fat),
					'total_carbs': float(meal.total_carbs),
					'food_count': meal.meal_foods.count(),
					'created_at': meal.created_at.isoformat()
				})
			
			return {
				'success': True,
				'meals': results,
				'pagination': {
					'page': page,
					'page_size': page_size,
					'total_pages': paginator.num_pages,
					'total_count': paginator.count,
					'has_next': page_obj.has_next(),
					'has_previous': page_obj.has_previous()
				}
			}
			
		except Exception as e:
			logger.error(f"Failed to get user meals: {str(e)}")
			return {
				'success': False,
				'error': str(e)
			}
	
	def delete_meal(self, meal_id: int, user_id: int) -> Dict[str, Any]:
		"""Delete a meal"""
		
		try:
			with transaction.atomic():
				meal = Meal.objects.get(id=meal_id, user_id=user_id)
				meal_date = meal.date
				meal.delete()
				
				# Update daily summary
				self._update_daily_summary(user_id, meal_date)
				
				return {
					'success': True,
					'message': 'Meal deleted successfully'
				}
				
		except Meal.DoesNotExist:
			return {
				'success': False,
				'error': 'Meal not found'
			}
		except Exception as e:
			logger.error(f"Failed to delete meal: {str(e)}")
			return {
				'success': False,
				'error': str(e)
			}
	
	def get_daily_summary(self, user_id: int, date: datetime.date) -> Dict[str, Any]:
		"""Get daily nutrition summary"""
		
		try:
			# Get or create daily summary
			daily_summary, created = DailySummary.objects.get_or_create(
				user_id=user_id,
				date=date
			)
			
			if created:
				# Update from meals
				daily_summary.update_from_meals()
			
			return {
				'success': True,
				'summary': {
					'date': date.isoformat(),
					'total_calories': float(daily_summary.total_calories),
					'total_protein': float(daily_summary.total_protein),
					'total_fat': float(daily_summary.total_fat),
					'total_carbs': float(daily_summary.total_carbs),
					'total_fiber': float(daily_summary.total_fiber),
					'weight_recorded': float(daily_summary.weight_recorded) if daily_summary.weight_recorded else None,
					'updated_at': daily_summary.updated_at.isoformat()
				}
			}
			
		except Exception as e:
			logger.error(f"Failed to get daily summary: {str(e)}")
			return {
				'success': False,
				'error': str(e)
			}
	
	def get_nutrition_stats(self, user_id: int, start_date: datetime.date, end_date: datetime.date) -> Dict[str, Any]:
		"""Get nutrition statistics for a date range"""
		
		try:
			# Get daily summaries
			summaries = DailySummary.objects.filter(
				user_id=user_id,
				date__gte=start_date,
				date__lte=end_date
			).order_by('date')
			
			# Calculate totals and averages
			daily_data = []
			total_calories = 0
			total_protein = 0
			total_fat = 0
			total_carbs = 0
			total_fiber = 0
			days_count = 0
			
			for summary in summaries:
				daily_data.append({
					'date': summary.date.isoformat(),
					'calories': float(summary.total_calories),
					'protein': float(summary.total_protein),
					'fat': float(summary.total_fat),
					'carbs': float(summary.total_carbs),
					'fiber': float(summary.total_fiber),
					'weight': float(summary.weight_recorded) if summary.weight_recorded else None
				})
				
				total_calories += float(summary.total_calories)
				total_protein += float(summary.total_protein)
				total_fat += float(summary.total_fat)
				total_carbs += float(summary.total_carbs)
				total_fiber += float(summary.total_fiber)
				days_count += 1
			
			# Calculate averages
			avg_calories = total_calories / days_count if days_count > 0 else 0
			avg_protein = total_protein / days_count if days_count > 0 else 0
			avg_fat = total_fat / days_count if days_count > 0 else 0
			avg_carbs = total_carbs / days_count if days_count > 0 else 0
			avg_fiber = total_fiber / days_count if days_count > 0 else 0
			
			return {
				'success': True,
				'stats': {
					'date_range': {
						'start_date': start_date.isoformat(),
						'end_date': end_date.isoformat(),
						'days_count': days_count
					},
					'totals': {
						'calories': round(total_calories, 2),
						'protein': round(total_protein, 2),
						'fat': round(total_fat, 2),
						'carbs': round(total_carbs, 2),
						'fiber': round(total_fiber, 2)
					},
					'averages': {
						'calories': round(avg_calories, 2),
						'protein': round(avg_protein, 2),
						'fat': round(avg_fat, 2),
						'carbs': round(avg_carbs, 2),
						'fiber': round(avg_fiber, 2)
					},
					'daily_data': daily_data
				}
			}
			
		except Exception as e:
			logger.error(f"Failed to get nutrition stats: {str(e)}")
			return {
				'success': False,
				'error': str(e)
			}
	
	def record_weight(self, user_id: int, date: datetime.date, weight: Decimal) -> Dict[str, Any]:
		"""Record user's weight for a specific date"""
		
		try:
			# Get or create daily summary
			daily_summary, created = DailySummary.objects.get_or_create(
				user_id=user_id,
				date=date
			)
			
			# Update weight
			daily_summary.weight_recorded = weight
			daily_summary.save()
			
			if created:
				# Update from meals
				daily_summary.update_from_meals()
			
			return {
				'success': True,
				'message': 'Weight recorded successfully',
				'weight': float(weight),
				'date': date.isoformat()
			}
			
		except Exception as e:
			logger.error(f"Failed to record weight: {str(e)}")
			return {
				'success': False,
				'error': str(e)
			}
	
	def _update_daily_summary(self, user_id: int, date: datetime.date):
		"""Update daily summary after meal changes"""
		
		try:
			daily_summary, created = DailySummary.objects.get_or_create(
				user_id=user_id,
				date=date
			)
			
			daily_summary.update_from_meals()
			
		except Exception as e:
			logger.error(f"Failed to update daily summary: {str(e)}")
	
	def create_meal_plan(self, user_id: int, plan_data: Dict[str, Any]) -> Dict[str, Any]:
		"""Create multiple meals for a day (meal planning)"""
		
		try:
			with transaction.atomic():
				date = plan_data['date']
				meals_data = plan_data['meals']
				
				created_meals = []
				
				for meal_data in meals_data:
					# Create meal
					meal = Meal.objects.create(
						user_id=user_id,
						date=date,
						meal_type=meal_data['meal_type'],
						name=meal_data.get('name', ''),
						notes=meal_data.get('notes', '')
					)
					
					# Add foods
					foods_added = []
					for food_item in meal_data.get('foods', []):
						food = Food.objects.get(id=food_item['food_id'])
						
						meal_food = MealFood.objects.create(
							meal=meal,
							food=food,
							quantity=Decimal(str(food_item['quantity']))
						)
						
						foods_added.append({
							'food_id': food.id,
							'food_name': food.name,
							'quantity': float(meal_food.quantity),
							'calories': float(meal_food.calories)
						})
					
					created_meals.append({
						'meal_id': meal.id,
						'meal_type': meal.meal_type,
						'foods_added': foods_added,
						'total_calories': float(meal.total_calories)
					})
				
				# Update daily summary
				self._update_daily_summary(user_id, date)
				
				return {
					'success': True,
					'date': date.isoformat(),
					'meals_created': created_meals,
					'message': 'Meal plan created successfully'
				}
				
		except Food.DoesNotExist:
			return {
				'success': False,
				'error': 'One or more foods not found'
			}
		except Exception as e:
			logger.error(f"Failed to create meal plan: {str(e)}")
			return {
				'success': False,
				'error': str(e)
			}