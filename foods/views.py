"""
Food API views
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_http_methods
import logging

from .models import Food, FoodCategory
from .serializers import (
	FoodSerializer, FoodCategorySerializer, FoodSearchSerializer,
	USDAFoodSearchSerializer, USDANutritionSerializer,
	CreateFoodFromUSDASerializer, CustomFoodSerializer, FoodSearchLogSerializer
)
from .services import FoodDataService

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def search_foods(request):
	"""Search for foods in the database"""
	
	serializer = FoodSearchSerializer(data=request.GET)
	if not serializer.is_valid():
		return Response({
			'success': False,
			'errors': serializer.errors
		}, status=status.HTTP_400_BAD_REQUEST)
	
	query = serializer.validated_data['query']
	page = serializer.validated_data['page']
	page_size = serializer.validated_data['page_size']
	
	service = FoodDataService()
	result = service.search_foods(
		query=query,
		user_id=request.user.id,
		page=page,
		page_size=page_size
	)
	
	if result['success']:
		return Response({
			'success': True,
			'data': result
		})
	else:
		return Response({
			'success': False,
			'message': result.get('error', 'Search failed')
		}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_food_details(request, food_id):
	"""Get detailed information about a specific food"""
	
	service = FoodDataService()
	result = service.get_food_details(food_id)
	
	if result['success']:
		return Response({
			'success': True,
			'data': result['food']
		})
	else:
		return Response({
			'success': False,
			'message': result.get('error', 'Food not found')
		}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def search_usda_foods(request):
	"""Search USDA FoodData Central database"""
	
	serializer = USDAFoodSearchSerializer(data=request.GET)
	if not serializer.is_valid():
		return Response({
			'success': False,
			'errors': serializer.errors
		}, status=status.HTTP_400_BAD_REQUEST)
	
	query = serializer.validated_data['query']
	page_size = serializer.validated_data['page_size']
	
	service = FoodDataService()
	result = service.search_usda_foods(query, page_size)
	
	if result['success']:
		return Response({
			'success': True,
			'data': result
		})
	else:
		return Response({
			'success': False,
			'message': result.get('error', 'USDA search failed')
		}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_usda_nutrition(request, fdc_id):
	"""Get detailed nutrition information from USDA"""
	
	service = FoodDataService()
	result = service.get_usda_nutrition(fdc_id)
	
	if result['success']:
		return Response({
			'success': True,
			'data': result['nutrition_data']
		})
	else:
		return Response({
			'success': False,
			'message': result.get('error', 'Nutrition data not found')
		}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_food_from_usda(request):
	"""Create a food record from USDA data"""
	
	serializer = CreateFoodFromUSDASerializer(data=request.data)
	if not serializer.is_valid():
		return Response({
			'success': False,
			'errors': serializer.errors
		}, status=status.HTTP_400_BAD_REQUEST)
	
	fdc_id = serializer.validated_data['fdc_id']
	
	service = FoodDataService()
	result = service.create_food_from_usda(fdc_id, request.user.id)
	
	if result['success']:
		return Response({
			'success': True,
			'data': {
				'food_id': result['food_id'],
				'message': result['message']
			}
		}, status=status.HTTP_201_CREATED)
	else:
		return Response({
			'success': False,
			'message': result.get('error', 'Failed to create food')
		}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_custom_food(request):
	"""Create a custom food record"""
	
	serializer = CustomFoodSerializer(data=request.data)
	if not serializer.is_valid():
		return Response({
			'success': False,
			'errors': serializer.errors
		}, status=status.HTTP_400_BAD_REQUEST)
	
	service = FoodDataService()
	result = service.create_custom_food(serializer.validated_data, request.user.id)
	
	if result['success']:
		return Response({
			'success': True,
			'data': {
				'food_id': result['food_id'],
				'message': result['message']
			}
		}, status=status.HTTP_201_CREATED)
	else:
		return Response({
			'success': False,
			'message': result.get('error', 'Failed to create custom food')
		}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_food(request, food_id):
	"""Update a food record"""
	
	service = FoodDataService()
	result = service.update_food(food_id, request.data, request.user.id)
	
	if result['success']:
		return Response({
			'success': True,
			'message': result['message']
		})
	else:
		return Response({
			'success': False,
			'message': result.get('error', 'Failed to update food')
		}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_food(request, food_id):
	"""Delete a custom food record"""
	
	service = FoodDataService()
	result = service.delete_food(food_id, request.user.id)
	
	if result['success']:
		return Response({
			'success': True,
			'message': result['message']
		})
	else:
		return Response({
			'success': False,
			'message': result.get('error', 'Failed to delete food')
		}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_food_categories(request):
	"""Get all food categories"""
	
	service = FoodDataService()
	result = service.get_food_categories()
	
	if result['success']:
		return Response({
			'success': True,
			'data': result['categories']
		})
	else:
		return Response({
			'success': False,
			'message': result.get('error', 'Failed to get categories')
		}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_search_history(request):
	"""Get user's search history"""
	
	limit = int(request.GET.get('limit', 20))
	
	service = FoodDataService()
	result = service.get_user_search_history(request.user.id, limit)
	
	if result['success']:
		return Response({
			'success': True,
			'data': result['searches']
		})
	else:
		return Response({
			'success': False,
			'message': result.get('error', 'Failed to get search history')
		}, status=status.HTTP_400_BAD_REQUEST)
