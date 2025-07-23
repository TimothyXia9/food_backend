"""
Meals service for managing meal tracking and nutrition summaries
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from django.db.models import Q, Sum, Count
from django.db import transaction
from django.core.paginator import Paginator
from django.utils import timezone
import pytz
from decimal import Decimal

from .models import Meal, MealFood, DailySummary
from foods.models import Food
from foods.usda_service import get_usda_service

logger = logging.getLogger(__name__)


class MealsService:
	"""Service for managing meals and nutrition tracking"""
	
	def _parse_timezone_filters(self, filters: Dict[str, Any]) -> Q:
		"""
		Parse timezone-aware datetime filters with fallback to legacy date filters.
		All filtering is now based on UTC datetime comparisons against the 'date' field.
		"""
		query = Q()
		
		# Check if we have UTC datetime parameters (preferred)
		start_datetime_utc = filters.get('start_datetime_utc')
		end_datetime_utc = filters.get('end_datetime_utc')
		
		if start_datetime_utc or end_datetime_utc:
			# Use UTC datetime filtering - compare against date field which is UTC
			if start_datetime_utc:
				query &= Q(date__gte=start_datetime_utc)
			if end_datetime_utc:
				query &= Q(date__lte=end_datetime_utc)
			
			logger.debug(f"Using UTC datetime filtering: {start_datetime_utc} to {end_datetime_utc}")
			return query
		
		# Legacy date filtering: convert date strings to UTC datetime ranges
		# Frontend should send UTC datetime strings, but we support legacy date format for compatibility
		if filters.get('date'):
			# Convert single date to UTC datetime range (00:00:00 to 23:59:59 UTC)
			date_str = filters['date']
			try:
				from datetime import datetime
				import pytz
				start_utc = datetime.strptime(f"{date_str} 00:00:00", "%Y-%m-%d %H:%M:%S").replace(tzinfo=pytz.UTC)
				end_utc = datetime.strptime(f"{date_str} 23:59:59", "%Y-%m-%d %H:%M:%S").replace(tzinfo=pytz.UTC)
				query &= Q(date__gte=start_utc) & Q(date__lte=end_utc)
				logger.info(f"Retrieved {Meal.objects.filter(query).count()} meals using legacy date filtering")
			except ValueError as e:
				logger.error(f"Invalid date format: {date_str} - {e}")
		
		if filters.get('start_date'):
			try:
				from datetime import datetime
				import pytz
				start_utc = datetime.strptime(f"{filters['start_date']} 00:00:00", "%Y-%m-%d %H:%M:%S").replace(tzinfo=pytz.UTC)
				query &= Q(date__gte=start_utc)
			except ValueError as e:
				logger.error(f"Invalid start_date format: {filters['start_date']} - {e}")
		
		if filters.get('end_date'):
			try:
				from datetime import datetime
				import pytz
				end_utc = datetime.strptime(f"{filters['end_date']} 23:59:59", "%Y-%m-%d %H:%M:%S").replace(tzinfo=pytz.UTC)
				query &= Q(date__lte=end_utc)
			except ValueError as e:
				logger.error(f"Invalid end_date format: {filters['end_date']} - {e}")
		
		if filters.get('start_date') or filters.get('end_date') or filters.get('date'):
			logger.debug(f"Using legacy date filtering: {filters.get('start_date')} to {filters.get('end_date')}")
		
		return query
	
	def _convert_timezone_to_utc(self, dt: datetime, user_timezone: str) -> datetime:
		"""Convert a datetime from user timezone to UTC"""
		try:
			user_tz = pytz.timezone(user_timezone)
			# If datetime is naive, assume it's in user timezone
			if dt.tzinfo is None:
				dt = user_tz.localize(dt)
			else:
				# Convert to user timezone first, then to UTC
				dt = dt.astimezone(user_tz)
			
			return dt.astimezone(pytz.UTC)
		except Exception as e:
			logger.warning(f"Failed to convert timezone {user_timezone}: {str(e)}")
			# Return as-is if conversion fails
			return dt
	
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
						# Try to get existing food first
						try:
							food = Food.objects.get(id=food_item['food_id'])
						except Food.DoesNotExist:
							# Check if this is a USDA food that needs to be created
							food = self._create_usda_food_if_needed(food_item, user_id)
							if not food:
								logger.error(f"Food with ID {food_item['food_id']} not found and could not be created from USDA")
								continue
						
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
	
	def add_food_to_meal(self, meal_id: int, user_id: int, food_id: int, quantity: Decimal, food_data: Dict[str, Any] = None) -> Dict[str, Any]:
		"""Add a food item to an existing meal"""
		
		try:
			with transaction.atomic():
				# Get meal
				meal = Meal.objects.get(id=meal_id, user_id=user_id)
				
				# Try to get existing food first
				try:
					food = Food.objects.get(id=food_id)
				except Food.DoesNotExist:
					# Check if this is a USDA food that needs to be created
					if food_data:
						food = self._create_usda_food_if_needed(food_data, user_id)
						if not food:
							return {
								'success': False,
								'error': f'Food with ID {food_id} not found and could not be created from USDA data'
							}
					else:
						return {
							'success': False,
							'error': f'Food with ID {food_id} not found'
						}
				
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
			# Build base query
			query = Q(user_id=user_id)
			
			# Apply timezone-aware date/datetime filters
			timezone_query = self._parse_timezone_filters(filters)
			query &= timezone_query
			
			# Apply other filters
			if filters.get('meal_type'):
				query &= Q(meal_type=filters['meal_type'])
			
			# Get meals with proper ordering
			# When using UTC datetime filtering, order by created_at
			# When using legacy date filtering, order by date
			has_datetime_filters = filters.get('start_datetime_utc') or filters.get('end_datetime_utc')
			if has_datetime_filters:
				meals = Meal.objects.filter(query).order_by('-created_at', 'meal_type')
				logger.debug("Ordering by created_at (UTC datetime filtering)")
			else:
				meals = Meal.objects.filter(query).order_by('-date', 'meal_type')
				logger.debug("Ordering by date (legacy date filtering)")
			
			# Paginate
			page = filters.get('page', 1)
			page_size = filters.get('page_size', 20)
			
			paginator = Paginator(meals, page_size)
			page_obj = paginator.get_page(page)
			
			# Format results
			results = []
			for meal in page_obj.object_list:
				# Get foods for this meal
				meal_foods = meal.meal_foods.select_related('food').all()
				foods_data = []
				for meal_food in meal_foods:
					foods_data.append({
						'id': meal_food.id,
						'food': {
							'id': meal_food.food.id,
							'name': meal_food.food.name
						},
						'quantity': float(meal_food.quantity),
						'calories': float(meal_food.calories)
					})
				
				results.append({
					'id': meal.id,
					'date': meal.date.isoformat(),
					'meal_type': meal.meal_type,
					'name': meal.name,
					'total_calories': float(meal.total_calories),
					'total_protein': float(meal.total_protein),
					'total_fat': float(meal.total_fat),
					'total_carbs': float(meal.total_carbs),
					'foods': foods_data,
					'food_count': len(foods_data),
					'created_at': meal.created_at.isoformat()
				})
			
			# Add debug information about filtering method used
			filter_method = "UTC datetime" if has_datetime_filters else "legacy date"
			logger.info(f"Retrieved {len(results)} meals using {filter_method} filtering")
			
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
				},
				'filter_method': filter_method  # Debug info
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
	
	def get_meal_statistics(self, user_id: int, date: datetime.date, meal_type: str = None) -> Dict[str, Any]:
		"""Get comprehensive meal statistics for a specific date"""
		
		try:
			# Build query for meals
			query = Q(user_id=user_id, date=date)
			if meal_type:
				query &= Q(meal_type=meal_type)
			
			meals = Meal.objects.filter(query)
			
			# Calculate statistics
			total_meals = meals.count()
			total_calories = sum(meal.total_calories for meal in meals)
			total_protein = sum(meal.total_protein for meal in meals)
			total_fat = sum(meal.total_fat for meal in meals)
			total_carbs = sum(meal.total_carbs for meal in meals)
			
			# Get meal breakdown by type
			meal_breakdown = {}
			for meal in meals:
				meal_type_key = meal.meal_type
				if meal_type_key not in meal_breakdown:
					meal_breakdown[meal_type_key] = {
						'count': 0,
						'calories': 0,
						'protein': 0,
						'fat': 0,
						'carbs': 0,
						'foods': []
					}
				
				meal_breakdown[meal_type_key]['count'] += 1
				meal_breakdown[meal_type_key]['calories'] += float(meal.total_calories)
				meal_breakdown[meal_type_key]['protein'] += float(meal.total_protein)
				meal_breakdown[meal_type_key]['fat'] += float(meal.total_fat)
				meal_breakdown[meal_type_key]['carbs'] += float(meal.total_carbs)
				
				# Get foods for this meal
				for meal_food in meal.meal_foods.all():
					meal_breakdown[meal_type_key]['foods'].append({
						'name': meal_food.food.name,
						'quantity': float(meal_food.quantity),
						'calories': float(meal_food.calories)
					})
			
			# Get most consumed foods
			meal_foods = MealFood.objects.filter(meal__in=meals)
			food_stats = {}
			for meal_food in meal_foods:
				food_name = meal_food.food.name
				if food_name not in food_stats:
					food_stats[food_name] = {
						'total_quantity': 0,
						'total_calories': 0,
						'frequency': 0
					}
				
				food_stats[food_name]['total_quantity'] += float(meal_food.quantity)
				food_stats[food_name]['total_calories'] += float(meal_food.calories)
				food_stats[food_name]['frequency'] += 1
			
			# Sort foods by calories
			top_foods = sorted(food_stats.items(), key=lambda x: x[1]['total_calories'], reverse=True)[:10]
			
			return {
				'success': True,
				'statistics': {
					'date': date.isoformat(),
					'meal_type_filter': meal_type,
					'summary': {
						'total_meals': total_meals,
						'total_calories': round(float(total_calories), 2),
						'total_protein': round(float(total_protein), 2),
						'total_fat': round(float(total_fat), 2),
						'total_carbs': round(float(total_carbs), 2)
					},
					'meal_breakdown': meal_breakdown,
					'top_foods': [
						{
							'name': food_name,
							'total_quantity': round(stats['total_quantity'], 2),
							'total_calories': round(stats['total_calories'], 2),
							'frequency': stats['frequency']
						}
						for food_name, stats in top_foods
					]
				}
			}
			
		except Exception as e:
			logger.error(f"Failed to get meal statistics: {str(e)}")
			return {
				'success': False,
				'error': str(e)
			}
	
	def get_meal_statistics_with_filters(self, user_id: int, filters: Dict[str, Any]) -> Dict[str, Any]:
		"""Get comprehensive meal statistics with flexible filtering"""
		
		try:
			# Build base query
			query = Q(user_id=user_id)
			
			# Apply timezone-aware date/datetime filters
			timezone_query = self._parse_timezone_filters(filters)
			query &= timezone_query
			
			# Apply meal type filter
			if filters.get('meal_type'):
				query &= Q(meal_type=filters['meal_type'])
			
			meals = Meal.objects.filter(query)
			
			# Calculate statistics
			total_meals = meals.count()
			total_calories = sum(meal.total_calories for meal in meals)
			total_protein = sum(meal.total_protein for meal in meals)
			total_fat = sum(meal.total_fat for meal in meals)
			total_carbs = sum(meal.total_carbs for meal in meals)
			
			# Get meal breakdown by type
			meal_breakdown = {}
			for meal in meals:
				meal_type_key = meal.meal_type
				if meal_type_key not in meal_breakdown:
					meal_breakdown[meal_type_key] = {
						'count': 0,
						'calories': 0,
						'protein': 0,
						'fat': 0,
						'carbs': 0,
						'foods': []
					}
				
				meal_breakdown[meal_type_key]['count'] += 1
				meal_breakdown[meal_type_key]['calories'] += float(meal.total_calories)
				meal_breakdown[meal_type_key]['protein'] += float(meal.total_protein)
				meal_breakdown[meal_type_key]['fat'] += float(meal.total_fat)
				meal_breakdown[meal_type_key]['carbs'] += float(meal.total_carbs)
				
				# Get foods for this meal
				for meal_food in meal.meal_foods.all():
					meal_breakdown[meal_type_key]['foods'].append({
						'name': meal_food.food.name,
						'quantity': float(meal_food.quantity),
						'calories': float(meal_food.calories)
					})
			
			# Get most consumed foods
			meal_foods = MealFood.objects.filter(meal__in=meals)
			food_stats = {}
			for meal_food in meal_foods:
				food_name = meal_food.food.name
				if food_name not in food_stats:
					food_stats[food_name] = {
						'total_quantity': 0,
						'total_calories': 0,
						'frequency': 0
					}
				
				food_stats[food_name]['total_quantity'] += float(meal_food.quantity)
				food_stats[food_name]['total_calories'] += float(meal_food.calories)
				food_stats[food_name]['frequency'] += 1
			
			# Sort foods by calories consumed
			top_foods = sorted(
				food_stats.items(),
				key=lambda x: x[1]['total_calories'],
				reverse=True
			)[:10]
			
			# Format response
			date_info = {}
			if filters.get('date'):
				date_info['date'] = filters['date'].isoformat() if hasattr(filters['date'], 'isoformat') else str(filters['date'])
			elif filters.get('start_datetime_utc') and filters.get('end_datetime_utc'):
				date_info['start_datetime_utc'] = filters['start_datetime_utc'].isoformat()
				date_info['end_datetime_utc'] = filters['end_datetime_utc'].isoformat()
			
			return {
				'success': True,
				'statistics': {
					**date_info,
					'meal_type_filter': filters.get('meal_type'),
					'summary': {
						'total_meals': total_meals,
						'total_calories': round(float(total_calories), 2),
						'total_protein': round(float(total_protein), 2),
						'total_fat': round(float(total_fat), 2),
						'total_carbs': round(float(total_carbs), 2)
					},
					'meal_breakdown': meal_breakdown,
					'top_foods': [
						{
							'name': food_name,
							'total_quantity': round(stats['total_quantity'], 2),
							'total_calories': round(stats['total_calories'], 2),
							'frequency': stats['frequency']
						}
						for food_name, stats in top_foods
					]
				}
			}
			
		except Exception as e:
			logger.error(f"Failed to get meal statistics with filters: {str(e)}")
			return {
				'success': False,
				'error': str(e)
			}
	
	def get_meal_comparison(self, user_id: int, date1: datetime.date, date2: datetime.date, meal_type: str = None) -> Dict[str, Any]:
		"""Compare meals between two dates"""
		
		try:
			# Get statistics for both dates
			stats1 = self.get_meal_statistics(user_id, date1, meal_type)
			stats2 = self.get_meal_statistics(user_id, date2, meal_type)
			
			if not stats1['success'] or not stats2['success']:
				return {
					'success': False,
					'error': 'Failed to get statistics for comparison'
				}
			
			# Calculate differences
			summary1 = stats1['statistics']['summary']
			summary2 = stats2['statistics']['summary']
			
			differences = {
				'total_meals': summary2['total_meals'] - summary1['total_meals'],
				'total_calories': round(summary2['total_calories'] - summary1['total_calories'], 2),
				'total_protein': round(summary2['total_protein'] - summary1['total_protein'], 2),
				'total_fat': round(summary2['total_fat'] - summary1['total_fat'], 2),
				'total_carbs': round(summary2['total_carbs'] - summary1['total_carbs'], 2)
			}
			
			# Calculate percentage changes
			percent_changes = {}
			for key in ['total_calories', 'total_protein', 'total_fat', 'total_carbs']:
				if summary1[key] > 0:
					percent_changes[key] = round((differences[key] / summary1[key]) * 100, 2)
				else:
					percent_changes[key] = 0
			
			return {
				'success': True,
				'comparison': {
					'date1': date1.isoformat(),
					'date2': date2.isoformat(),
					'meal_type_filter': meal_type,
					'date1_stats': stats1['statistics'],
					'date2_stats': stats2['statistics'],
					'differences': differences,
					'percent_changes': percent_changes
				}
			}
			
		except Exception as e:
			logger.error(f"Failed to get meal comparison: {str(e)}")
			return {
				'success': False,
				'error': str(e)
			}
	
	def _create_usda_food_if_needed(self, food_item: Dict[str, Any], user_id: int) -> Optional[Food]:
		"""
		Create a Food record from USDA data if the food_item contains USDA information.
		This allows USDA foods to be automatically added to the local database when 
		they're added to meal baskets.
		
		Args:
			food_item: Dictionary containing food information including potential USDA data
			user_id: ID of the user creating the meal
			
		Returns:
			Food instance if created successfully, None otherwise
		"""
		try:
			# Check if this food_item contains USDA information
			fdc_id = food_item.get('fdc_id') or food_item.get('usda_fdc_id')
			if not fdc_id:
				logger.debug(f"No USDA FDC ID found in food_item: {food_item}")
				return None
			
			# Check if we already have this USDA food in our database
			existing_food = Food.objects.filter(usda_fdc_id=str(fdc_id)).first()
			if existing_food:
				logger.info(f"Found existing USDA food with FDC ID {fdc_id}: {existing_food.name}")
				return existing_food
			
			# Get USDA service and fetch nutrition data
			usda_service = get_usda_service()
			if not usda_service.is_available():
				logger.warning("USDA service not available for creating food")
				return None
			
			# Get detailed nutrition data from USDA
			result = usda_service.get_food_details(int(fdc_id))
			if not result['success']:
				logger.error(f"Failed to get USDA nutrition data for FDC ID {fdc_id}: {result.get('error')}")
				return None
			
			nutrition_data = result['nutrition_data']
			nutrients = nutrition_data.get('nutrients', {})
			
			# Create the food record
			food = Food.objects.create(
				name=nutrition_data.get('description', food_item.get('name', f'USDA Food {fdc_id}')),
				serving_size=100,  # USDA data is per 100g
				calories_per_100g=nutrients.get('calories', {}).get('amount', 0),
				protein_per_100g=nutrients.get('protein', {}).get('amount', 0),
				fat_per_100g=nutrients.get('fat', {}).get('amount', 0),
				carbs_per_100g=nutrients.get('carbs', {}).get('amount', 0),
				fiber_per_100g=nutrients.get('fiber', {}).get('amount', 0),
				sugar_per_100g=nutrients.get('sugar', {}).get('amount', 0),
				sodium_per_100g=nutrients.get('sodium', {}).get('amount', 0),
				is_verified=True,  # USDA data is verified
				usda_fdc_id=str(fdc_id),
				created_by_id=user_id
			)
			
			logger.info(f"Successfully created USDA food: {food.name} (FDC ID: {fdc_id})")
			return food
			
		except Exception as e:
			logger.error(f"Failed to create USDA food from food_item {food_item}: {str(e)}")
			return None