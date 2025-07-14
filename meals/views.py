"""
Meals API views for meal tracking and nutrition summaries
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from datetime import datetime, timedelta
import logging

from .models import Meal, MealFood, DailySummary
from .serializers import (
	MealSerializer, CreateMealSerializer, AddFoodToMealSerializer,
	UpdateMealFoodSerializer, DailySummarySerializer, MealListSerializer,
	NutritionStatsSerializer, WeightRecordSerializer, MealPlanSerializer
)
from .services import MealsService

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_meal(request):
	"""Create a new meal"""
	
	serializer = CreateMealSerializer(data=request.data)
	if not serializer.is_valid():
		return Response({
			'success': False,
			'errors': serializer.errors
		}, status=status.HTTP_400_BAD_REQUEST)
	
	service = MealsService()
	result = service.create_meal(request.user.id, serializer.validated_data)
	
	if result['success']:
		return Response({
			'success': True,
			'data': result,
			'message': result['message']
		}, status=status.HTTP_201_CREATED)
	else:
		return Response({
			'success': False,
			'message': result.get('error', 'Failed to create meal')
		}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_meal_details(request, meal_id):
	"""Get detailed information about a meal"""
	
	service = MealsService()
	result = service.get_meal_details(meal_id, request.user.id)
	
	if result['success']:
		return Response({
			'success': True,
			'data': result['meal']
		})
	else:
		return Response({
			'success': False,
			'message': result.get('error', 'Meal not found')
		}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_food_to_meal(request, meal_id):
	"""Add a food item to an existing meal"""
	
	serializer = AddFoodToMealSerializer(data=request.data)
	if not serializer.is_valid():
		return Response({
			'success': False,
			'errors': serializer.errors
		}, status=status.HTTP_400_BAD_REQUEST)
	
	food_id = serializer.validated_data['food_id']
	quantity = serializer.validated_data['quantity']
	
	service = MealsService()
	result = service.add_food_to_meal(meal_id, request.user.id, food_id, quantity)
	
	if result['success']:
		return Response({
			'success': True,
			'data': result,
			'message': result['message']
		}, status=status.HTTP_201_CREATED)
	else:
		return Response({
			'success': False,
			'message': result.get('error', 'Failed to add food to meal')
		}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_meal_food(request, meal_food_id):
	"""Update the quantity of a food item in a meal"""
	
	serializer = UpdateMealFoodSerializer(data=request.data)
	if not serializer.is_valid():
		return Response({
			'success': False,
			'errors': serializer.errors
		}, status=status.HTTP_400_BAD_REQUEST)
	
	quantity = serializer.validated_data['quantity']
	
	service = MealsService()
	result = service.update_meal_food(meal_food_id, request.user.id, quantity)
	
	if result['success']:
		return Response({
			'success': True,
			'data': result,
			'message': result['message']
		})
	else:
		return Response({
			'success': False,
			'message': result.get('error', 'Failed to update food quantity')
		}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def remove_food_from_meal(request, meal_food_id):
	"""Remove a food item from a meal"""
	
	service = MealsService()
	result = service.remove_food_from_meal(meal_food_id, request.user.id)
	
	if result['success']:
		return Response({
			'success': True,
			'message': result['message']
		})
	else:
		return Response({
			'success': False,
			'message': result.get('error', 'Failed to remove food from meal')
		}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_meals(request):
	"""Get user's meals with optional filtering"""
	
	serializer = MealListSerializer(data=request.GET)
	if not serializer.is_valid():
		return Response({
			'success': False,
			'errors': serializer.errors
		}, status=status.HTTP_400_BAD_REQUEST)
	
	service = MealsService()
	result = service.get_user_meals(request.user.id, serializer.validated_data)
	
	if result['success']:
		return Response({
			'success': True,
			'data': result
		})
	else:
		return Response({
			'success': False,
			'message': result.get('error', 'Failed to get meals')
		}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_meal(request, meal_id):
	"""Delete a meal"""
	
	service = MealsService()
	result = service.delete_meal(meal_id, request.user.id)
	
	if result['success']:
		return Response({
			'success': True,
			'message': result['message']
		})
	else:
		return Response({
			'success': False,
			'message': result.get('error', 'Failed to delete meal')
		}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_daily_summary(request):
	"""Get daily nutrition summary"""
	
	date_str = request.GET.get('date')
	if not date_str:
		return Response({
			'success': False,
			'message': 'Date parameter is required'
		}, status=status.HTTP_400_BAD_REQUEST)
	
	try:
		date = datetime.strptime(date_str, '%Y-%m-%d').date()
	except ValueError:
		return Response({
			'success': False,
			'message': 'Invalid date format. Use YYYY-MM-DD'
		}, status=status.HTTP_400_BAD_REQUEST)
	
	service = MealsService()
	result = service.get_daily_summary(request.user.id, date)
	
	if result['success']:
		return Response({
			'success': True,
			'data': result['summary']
		})
	else:
		return Response({
			'success': False,
			'message': result.get('error', 'Failed to get daily summary')
		}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_nutrition_stats(request):
	"""Get nutrition statistics for a date range"""
	
	serializer = NutritionStatsSerializer(data=request.GET)
	if not serializer.is_valid():
		return Response({
			'success': False,
			'errors': serializer.errors
		}, status=status.HTTP_400_BAD_REQUEST)
	
	start_date = serializer.validated_data['start_date']
	end_date = serializer.validated_data['end_date']
	
	service = MealsService()
	result = service.get_nutrition_stats(request.user.id, start_date, end_date)
	
	if result['success']:
		return Response({
			'success': True,
			'data': result['stats']
		})
	else:
		return Response({
			'success': False,
			'message': result.get('error', 'Failed to get nutrition stats')
		}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def record_weight(request):
	"""Record user's weight for a specific date"""
	
	serializer = WeightRecordSerializer(data=request.data)
	if not serializer.is_valid():
		return Response({
			'success': False,
			'errors': serializer.errors
		}, status=status.HTTP_400_BAD_REQUEST)
	
	date = serializer.validated_data['date']
	weight = serializer.validated_data['weight']
	
	service = MealsService()
	result = service.record_weight(request.user.id, date, weight)
	
	if result['success']:
		return Response({
			'success': True,
			'data': {
				'date': result['date'],
				'weight': result['weight']
			},
			'message': result['message']
		}, status=status.HTTP_201_CREATED)
	else:
		return Response({
			'success': False,
			'message': result.get('error', 'Failed to record weight')
		}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_meal_plan(request):
	"""Create multiple meals for a day (meal planning)"""
	
	serializer = MealPlanSerializer(data=request.data)
	if not serializer.is_valid():
		return Response({
			'success': False,
			'errors': serializer.errors
		}, status=status.HTTP_400_BAD_REQUEST)
	
	service = MealsService()
	result = service.create_meal_plan(request.user.id, serializer.validated_data)
	
	if result['success']:
		return Response({
			'success': True,
			'data': result,
			'message': result['message']
		}, status=status.HTTP_201_CREATED)
	else:
		return Response({
			'success': False,
			'message': result.get('error', 'Failed to create meal plan')
		}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_recent_meals(request):
	"""Get user's recent meals"""
	
	try:
		days = int(request.GET.get('days', 7))
		end_date = datetime.now().date()
		start_date = end_date - timedelta(days=days)
		
		service = MealsService()
		result = service.get_user_meals(request.user.id, {
			'start_date': start_date,
			'end_date': end_date,
			'page': 1,
			'page_size': 50
		})
		
		if result['success']:
			return Response({
				'success': True,
				'data': result
			})
		else:
			return Response({
				'success': False,
				'message': result.get('error', 'Failed to get recent meals')
			}, status=status.HTTP_400_BAD_REQUEST)
			
	except ValueError:
		return Response({
			'success': False,
			'message': 'Invalid days parameter'
		}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_meal(request, meal_id):
	"""Update meal details"""
	
	try:
		meal = Meal.objects.get(id=meal_id, user=request.user)
		
		# Update allowed fields
		if 'name' in request.data:
			meal.name = request.data['name']
		if 'notes' in request.data:
			meal.notes = request.data['notes']
		if 'meal_type' in request.data:
			meal.meal_type = request.data['meal_type']
		
		meal.save()
		
		return Response({
			'success': True,
			'message': 'Meal updated successfully'
		})
		
	except Meal.DoesNotExist:
		return Response({
			'success': False,
			'message': 'Meal not found'
		}, status=status.HTTP_404_NOT_FOUND)
	except Exception as e:
		logger.error(f"Failed to update meal: {str(e)}")
		return Response({
			'success': False,
			'message': f'Failed to update meal: {str(e)}'
		}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
