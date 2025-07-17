"""
Food API views
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_http_methods
import logging

from .models import Food, FoodAlias, FoodSearchLog
from .serializers import (
	FoodSerializer, FoodSearchSerializer,
	USDAFoodSearchSerializer, USDANutritionSerializer,
	CreateFoodFromUSDASerializer, CustomFoodSerializer, FoodSearchLogSerializer
)
from .usda_service import get_usda_service

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([AllowAny])
def search_foods(request):
	"""Search for foods - now uses USDA as primary source with local fallback"""
	
	try:
		# Get search parameters
		query = request.GET.get('query', '').strip()
		page = int(request.GET.get('page', 1))
		page_size = int(request.GET.get('page_size', 20))
		
		if not query:
			return Response({
				'success': False,
				'error': {
					'code': 'VALIDATION_ERROR',
					'message': 'Query parameter is required'
				}
			}, status=status.HTTP_400_BAD_REQUEST)
		
		# Try USDA search first
		from .usda_service import get_usda_service
		usda_service = get_usda_service()
		
		if usda_service.is_available():
			# Search USDA database
			result = usda_service.search_foods(query, min(page_size, 25), page)
			
			if result['success']:
				# Format the results for our API
				foods_data = []
				for food in result.get('foods', []):
					# Get complete food name with brand if available
					food_name = food.get('description', '')
					brand_owner = food.get('brandOwner', '')
					
					# Create a more complete name
					if brand_owner and brand_owner.lower() not in food_name.lower():
						display_name = f"{brand_owner} - {food_name}"
					else:
						display_name = food_name
					
					# Extract nutrition data from search result
					nutrition = usda_service._extract_nutrition_from_search_result(food)
					
					food_data = {
						'id': food.get('fdcId'),
						'fdc_id': food.get('fdcId'),
						'name': display_name,
						'brand': brand_owner,
						'data_type': food.get('dataType'),
						'publication_date': food.get('publicationDate'),
						'is_usda': True,
						'category': {'name': 'USDA Food'},
						'serving_size': 100,
						'is_custom': False
					}
					
					# Add nutrition data
					food_data.update(nutrition)
					foods_data.append(food_data)
				
				# Log the search
				if request.user.is_authenticated:
					try:
						FoodSearchLog.objects.create(
							user=request.user,
							query=query,
							results_count=len(foods_data),
							source='USDA'
						)
					except Exception as e:
						print(f"Warning: Could not log search: {e}")
				
				return Response({
					'success': True,
					'data': {
						'foods': foods_data,
						'total_count': result.get('total_hits', len(foods_data)),
						'page': page,
						'page_size': page_size,
						'total_pages': max(1, (result.get('total_hits', len(foods_data)) + page_size - 1) // page_size),
						'source': 'USDA'
					}
				}, status=status.HTTP_200_OK)
		
		# Fallback to local search if USDA is not available
		from django.db.models import Q
		
		foods_queryset = Food.objects.filter(
			Q(name__icontains=query) | Q(aliases__alias__icontains=query)
		).select_related('created_by').distinct().order_by('name')
		
		# Pagination
		total_count = foods_queryset.count()
		total_pages = (total_count + page_size - 1) // page_size
		start_index = (page - 1) * page_size
		end_index = start_index + page_size
		foods = foods_queryset[start_index:end_index]
		
		# Serialize the results
		foods_data = []
		for food in foods:
			foods_data.append({
				'id': food.id,
				'name': food.name,
				'brand': food.brand,
				'calories_per_100g': float(food.calories_per_100g),
				'protein_per_100g': float(food.protein_per_100g) if food.protein_per_100g else None,
				'fat_per_100g': float(food.fat_per_100g) if food.fat_per_100g else None,
				'carbs_per_100g': float(food.carbs_per_100g) if food.carbs_per_100g else None,
				'fiber_per_100g': float(food.fiber_per_100g) if food.fiber_per_100g else None,
				'sugar_per_100g': float(food.sugar_per_100g) if food.sugar_per_100g else None,
				'sodium_per_100g': float(food.sodium_per_100g) if food.sodium_per_100g else None,
				'serving_size': float(food.serving_size),
				'is_custom': food.is_custom,
				'is_verified': food.is_verified,
				'is_usda': False,
				'category': {'name': food.category.name if food.category else 'Unknown'}
			})
		
		# Log the search
		if request.user.is_authenticated:
			try:
				FoodSearchLog.objects.create(
					user=request.user,
					query=query,
					results_count=total_count,
					source='LOCAL'
				)
			except Exception as log_error:
				logger.warning(f"Failed to log search: {log_error}")
		
		return Response({
			'success': True,
			'data': {
				'foods': foods_data,
				'total_count': total_count,
				'page': page,
				'page_size': page_size,
				'total_pages': total_pages,
				'source': 'LOCAL'
			},
			'message': f"Found {total_count} foods matching '{query}'"
		})
		
	except ValueError as e:
		return Response({
			'success': False,
			'error': {
				'code': 'VALIDATION_ERROR',
				'message': 'Invalid page or page_size parameter'
			}
		}, status=status.HTTP_400_BAD_REQUEST)
	except Exception as e:
		logger.error(f"Error in search_foods: {e}")
		return Response({
			'success': False,
			'error': {
				'code': 'SERVER_ERROR',
				'message': 'An error occurred while searching foods'
			}
		}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_food_details(request, food_id):
	"""Get detailed information about a specific food"""
	
	try:
		food = Food.objects.select_related('category', 'created_by').get(id=food_id)
		
		food_data = {
			'id': food.id,
			'name': food.name,
			'brand': food.brand,
			'barcode': food.barcode,
			'category': {
				'id': food.category.id,
				'name': food.category.name
			} if food.category else None,
			'serving_size': float(food.serving_size),
			'calories_per_100g': float(food.calories_per_100g),
			'protein_per_100g': float(food.protein_per_100g) if food.protein_per_100g else None,
			'fat_per_100g': float(food.fat_per_100g) if food.fat_per_100g else None,
			'carbs_per_100g': float(food.carbs_per_100g) if food.carbs_per_100g else None,
			'fiber_per_100g': float(food.fiber_per_100g) if food.fiber_per_100g else None,
			'sugar_per_100g': float(food.sugar_per_100g) if food.sugar_per_100g else None,
			'sodium_per_100g': float(food.sodium_per_100g) if food.sodium_per_100g else None,
			'is_custom': food.is_custom,
			'is_verified': food.is_verified,
			'created_by': food.created_by.username if food.created_by else None,
			'created_at': food.created_at.isoformat(),
			'updated_at': food.updated_at.isoformat()
		}
		
		return Response({
			'success': True,
			'data': food_data,
			'message': f'Retrieved details for {food.name}'
		})
		
	except Food.DoesNotExist:
		return Response({
			'success': False,
			'error': {
				'code': 'NOT_FOUND',
				'message': 'Food not found'
			}
		}, status=status.HTTP_404_NOT_FOUND)
	except Exception as e:
		logger.error(f"Error in get_food_details: {e}")
		return Response({
			'success': False,
			'error': {
				'code': 'SERVER_ERROR',
				'message': 'An error occurred while getting food details'
			}
		}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def search_usda_foods(request):
	"""Search USDA FoodData Central database"""
	
	try:
		# Get search parameters
		query = request.GET.get('query', '').strip()
		page_size = int(request.GET.get('page_size', 25))
		page_number = int(request.GET.get('page', 1))
		
		if not query:
			return Response({
				'success': False,
				'error': {
					'code': 'VALIDATION_ERROR',
					'message': 'Query parameter is required'
				}
			}, status=status.HTTP_400_BAD_REQUEST)
		
		# Get USDA service
		usda_service = get_usda_service()
		
		if not usda_service.is_available():
			return Response({
				'success': False,
				'error': {
					'code': 'SERVICE_UNAVAILABLE',
					'message': 'USDA API service is not configured. Please add USDA_API_KEY to environment variables.'
				}
			}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
		
		# Search USDA database
		result = usda_service.search_foods(query, page_size, page_number)
		
		if result['success']:
			# Format the results for our API
			foods_data = []
			for food in result.get('foods', []):
				foods_data.append({
					'fdc_id': food.get('fdcId'),
					'description': food.get('description'),
					'data_type': food.get('dataType'),
					'publication_date': food.get('publicationDate'),
					'brand_owner': food.get('brandOwner'),
					'ingredients': food.get('ingredients'),
					'score': food.get('score', 0)
				})
			
			return Response({
				'success': True,
				'data': {
					'foods': foods_data,
					'total_hits': result.get('total_hits', 0),
					'current_page': result.get('current_page', page_number),
					'total_pages': result.get('total_pages', 1),
					'query': query
				},
				'message': f"Found {result.get('total_hits', 0)} USDA foods matching '{query}'"
			})
		else:
			return Response({
				'success': False,
				'error': {
					'code': 'USDA_API_ERROR',
					'message': result.get('error', 'USDA search failed')
				}
			}, status=status.HTTP_400_BAD_REQUEST)
			
	except ValueError as e:
		return Response({
			'success': False,
			'error': {
				'code': 'VALIDATION_ERROR',
				'message': 'Invalid page or page_size parameter'
			}
		}, status=status.HTTP_400_BAD_REQUEST)
	except Exception as e:
		logger.error(f"Error in search_usda_foods: {e}")
		return Response({
			'success': False,
			'error': {
				'code': 'SERVER_ERROR',
				'message': 'An error occurred while searching USDA foods'
			}
		}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_usda_nutrition(request, fdc_id):
	"""Get detailed nutrition information from USDA"""
	
	try:
		# Get USDA service
		usda_service = get_usda_service()
		
		if not usda_service.is_available():
			return Response({
				'success': False,
				'error': {
					'code': 'SERVICE_UNAVAILABLE',
					'message': 'USDA API service is not configured'
				}
			}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
		
		# Get nutrition details
		result = usda_service.get_food_details(int(fdc_id))
		
		if result['success']:
			nutrition_data = result['nutrition_data']
			
			# Format the nutrition data to match our API structure
			formatted_data = {
				'id': nutrition_data.get('fdc_id'),
				'fdc_id': nutrition_data.get('fdc_id'),
				'name': nutrition_data.get('description'),
				'brand': nutrition_data.get('brand_owner', ''),
				'data_type': nutrition_data.get('data_type'),
				'publication_date': nutrition_data.get('publication_date'),
				'is_usda': True,
				'calories_per_100g': nutrition_data.get('calories_per_100g', 0),
				'protein_per_100g': nutrition_data.get('protein_per_100g', 0),
				'fat_per_100g': nutrition_data.get('fat_per_100g', 0),
				'carbs_per_100g': nutrition_data.get('carbs_per_100g', 0),
				'fiber_per_100g': nutrition_data.get('fiber_per_100g', 0),
				'sugar_per_100g': nutrition_data.get('sugar_per_100g', 0),
				'sodium_per_100g': nutrition_data.get('sodium_per_100g', 0),
				'category': {'name': 'USDA Food'},
				'serving_size': 100,
				'is_custom': False,
				'is_verified': True,
				'ingredients': nutrition_data.get('ingredients', ''),
				'nutrients': nutrition_data.get('nutrients', [])
			}
			
			return Response({
				'success': True,
				'data': formatted_data,
				'message': f"Retrieved nutrition data for FDC ID {fdc_id}"
			})
		else:
			return Response({
				'success': False,
				'error': {
					'code': 'USDA_API_ERROR',
					'message': result.get('error', 'Nutrition data not found')
				}
			}, status=status.HTTP_404_NOT_FOUND)
			
	except ValueError as e:
		return Response({
			'success': False,
			'error': {
				'code': 'VALIDATION_ERROR',
				'message': 'Invalid FDC ID format'
			}
		}, status=status.HTTP_400_BAD_REQUEST)
	except Exception as e:
		logger.error(f"Error in get_usda_nutrition: {e}")
		return Response({
			'success': False,
			'error': {
				'code': 'SERVER_ERROR',
				'message': 'An error occurred while getting nutrition data'
			}
		}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_food_from_usda(request):
	"""Create a food record from USDA data"""
	
	try:
		fdc_id = request.data.get('fdc_id')
		if not fdc_id:
			return Response({
				'success': False,
				'error': {
					'code': 'VALIDATION_ERROR',
					'message': 'fdc_id is required'
				}
			}, status=status.HTTP_400_BAD_REQUEST)
		
		# Get USDA service
		usda_service = get_usda_service()
		
		if not usda_service.is_available():
			return Response({
				'success': False,
				'error': {
					'code': 'SERVICE_UNAVAILABLE',
					'message': 'USDA API service is not configured'
				}
			}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
		
		# Get nutrition data from USDA
		result = usda_service.get_food_details(int(fdc_id))
		
		if not result['success']:
			return Response({
				'success': False,
				'error': {
					'code': 'USDA_API_ERROR',
					'message': result.get('error', 'Failed to get USDA data')
				}
			}, status=status.HTTP_400_BAD_REQUEST)
		
		nutrition_data = result['nutrition_data']
		nutrients = nutrition_data.get('nutrients', {})
		
		# Create food record
		food = Food.objects.create(
			name=nutrition_data.get('description', f'USDA Food {fdc_id}'),
			serving_size=100,  # USDA data is per 100g
			calories_per_100g=nutrients.get('calories', {}).get('amount', 0),
			protein_per_100g=nutrients.get('protein', {}).get('amount'),
			fat_per_100g=nutrients.get('fat', {}).get('amount'),
			carbs_per_100g=nutrients.get('carbs', {}).get('amount'),
			fiber_per_100g=nutrients.get('fiber', {}).get('amount'),
			sugar_per_100g=nutrients.get('sugar', {}).get('amount'),
			sodium_per_100g=nutrients.get('sodium', {}).get('amount'),
			is_verified=True,  # USDA data is verified
			created_by=request.user
		)
		
		return Response({
			'success': True,
			'data': {
				'food_id': food.id,
				'name': food.name,
				'fdc_id': fdc_id
			},
			'message': f'Successfully created food from USDA data (FDC ID: {fdc_id})'
		}, status=status.HTTP_201_CREATED)
		
	except ValueError as e:
		return Response({
			'success': False,
			'error': {
				'code': 'VALIDATION_ERROR',
				'message': 'Invalid FDC ID format'
			}
		}, status=status.HTTP_400_BAD_REQUEST)
	except Exception as e:
		logger.error(f"Error in create_food_from_usda: {e}")
		return Response({
			'success': False,
			'error': {
				'code': 'SERVER_ERROR',
				'message': 'An error occurred while creating food from USDA data'
			}
		}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
