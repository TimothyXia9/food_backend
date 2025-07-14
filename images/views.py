"""
Image API views for food recognition
"""

import asyncio
import os
from PIL import Image
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.core.files.storage import default_storage
from django.utils import timezone
import logging

from .models import UploadedImage, FoodRecognitionResult
from .serializers import (
	UploadedImageSerializer, ImageUploadSerializer, 
	FoodRecognitionResultSerializer, ImageAnalysisRequestSerializer,
	ConfirmFoodRecognitionSerializer, CreateMealFromImageSerializer
)
from .services import FoodImageAnalysisService

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_image(request):
	"""Upload an image for food recognition"""
	
	serializer = ImageUploadSerializer(data=request.data)
	if not serializer.is_valid():
		return Response({
			'success': False,
			'errors': serializer.errors
		}, status=status.HTTP_400_BAD_REQUEST)
	
	try:
		image_file = serializer.validated_data['image']
		meal_id = serializer.validated_data.get('meal_id')
		
		# Get image dimensions
		pil_image = Image.open(image_file)
		width, height = pil_image.size
		
		# Create image record
		uploaded_image = UploadedImage.objects.create(
			user=request.user,
			meal_id=meal_id,
			filename=image_file.name,
			file_path=image_file,
			file_size=image_file.size,
			mime_type=image_file.content_type,
			width=width,
			height=height,
			processing_status='pending'
		)
		
		# Serialize response
		serializer = UploadedImageSerializer(uploaded_image)
		
		return Response({
			'success': True,
			'data': serializer.data,
			'message': 'Image uploaded successfully'
		}, status=status.HTTP_201_CREATED)
		
	except Exception as e:
		logger.error(f"Image upload failed: {str(e)}")
		return Response({
			'success': False,
			'message': f'Image upload failed: {str(e)}'
		}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def analyze_image(request):
	"""Analyze an uploaded image for food recognition"""
	
	serializer = ImageAnalysisRequestSerializer(data=request.data)
	if not serializer.is_valid():
		return Response({
			'success': False,
			'errors': serializer.errors
		}, status=status.HTTP_400_BAD_REQUEST)
	
	image_id = serializer.validated_data['image_id']
	
	try:
		# Run async analysis in sync wrapper
		service = FoodImageAnalysisService()
		result = asyncio.run(service.analyze_image(image_id, request.user.id))
		
		if result['success']:
			return Response({
				'success': True,
				'data': result,
				'message': 'Image analysis completed successfully'
			})
		else:
			return Response({
				'success': False,
				'message': result.get('error', 'Image analysis failed')
			}, status=status.HTTP_400_BAD_REQUEST)
			
	except Exception as e:
		logger.error(f"Image analysis failed: {str(e)}")
		return Response({
			'success': False,
			'message': f'Image analysis failed: {str(e)}'
		}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_image_results(request, image_id):
	"""Get analysis results for an image"""
	
	try:
		service = FoodImageAnalysisService()
		result = service.get_image_analysis_results(image_id, request.user.id)
		
		if result['success']:
			return Response({
				'success': True,
				'data': result
			})
		else:
			return Response({
				'success': False,
				'message': result.get('error', 'Results not found')
			}, status=status.HTTP_404_NOT_FOUND)
			
	except Exception as e:
		logger.error(f"Failed to get image results: {str(e)}")
		return Response({
			'success': False,
			'message': f'Failed to get results: {str(e)}'
		}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def confirm_food_recognition(request):
	"""Confirm or reject a food recognition result"""
	
	serializer = ConfirmFoodRecognitionSerializer(data=request.data)
	if not serializer.is_valid():
		return Response({
			'success': False,
			'errors': serializer.errors
		}, status=status.HTTP_400_BAD_REQUEST)
	
	result_id = serializer.validated_data['result_id']
	is_confirmed = serializer.validated_data['is_confirmed']
	
	try:
		service = FoodImageAnalysisService()
		result = service.confirm_food_recognition(result_id, request.user.id, is_confirmed)
		
		if result['success']:
			return Response({
				'success': True,
				'data': result,
				'message': 'Food recognition updated successfully'
			})
		else:
			return Response({
				'success': False,
				'message': result.get('error', 'Failed to update recognition')
			}, status=status.HTTP_400_BAD_REQUEST)
			
	except Exception as e:
		logger.error(f"Failed to confirm recognition: {str(e)}")
		return Response({
			'success': False,
			'message': f'Failed to confirm recognition: {str(e)}'
		}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_meal_from_image(request):
	"""Create a meal from confirmed food recognition results"""
	
	serializer = CreateMealFromImageSerializer(data=request.data)
	if not serializer.is_valid():
		return Response({
			'success': False,
			'errors': serializer.errors
		}, status=status.HTTP_400_BAD_REQUEST)
	
	image_id = serializer.validated_data['image_id']
	meal_type = serializer.validated_data['meal_type']
	date = serializer.validated_data.get('date')
	
	try:
		service = FoodImageAnalysisService()
		result = service.create_meal_from_image(
			image_id, 
			request.user.id, 
			meal_type, 
			date.strftime('%Y-%m-%d') if date else None
		)
		
		if result['success']:
			return Response({
				'success': True,
				'data': result,
				'message': 'Meal created successfully'
			}, status=status.HTTP_201_CREATED)
		else:
			return Response({
				'success': False,
				'message': result.get('error', 'Failed to create meal')
			}, status=status.HTTP_400_BAD_REQUEST)
			
	except Exception as e:
		logger.error(f"Failed to create meal from image: {str(e)}")
		return Response({
			'success': False,
			'message': f'Failed to create meal: {str(e)}'
		}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_images(request):
	"""Get user's uploaded images"""
	
	try:
		images = UploadedImage.objects.filter(user=request.user).order_by('-uploaded_at')
		
		# Pagination
		page = int(request.GET.get('page', 1))
		page_size = int(request.GET.get('page_size', 20))
		
		start = (page - 1) * page_size
		end = start + page_size
		
		paginated_images = images[start:end]
		
		serializer = UploadedImageSerializer(paginated_images, many=True)
		
		return Response({
			'success': True,
			'data': {
				'images': serializer.data,
				'pagination': {
					'page': page,
					'page_size': page_size,
					'total_count': images.count(),
					'has_next': end < images.count(),
					'has_previous': page > 1
				}
			}
		})
		
	except Exception as e:
		logger.error(f"Failed to get user images: {str(e)}")
		return Response({
			'success': False,
			'message': f'Failed to get images: {str(e)}'
		}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_image(request, image_id):
	"""Delete an uploaded image"""
	
	try:
		image = UploadedImage.objects.get(id=image_id, user=request.user)
		image.delete()
		
		return Response({
			'success': True,
			'message': 'Image deleted successfully'
		})
		
	except UploadedImage.DoesNotExist:
		return Response({
			'success': False,
			'message': 'Image not found'
		}, status=status.HTTP_404_NOT_FOUND)
		
	except Exception as e:
		logger.error(f"Failed to delete image: {str(e)}")
		return Response({
			'success': False,
			'message': f'Failed to delete image: {str(e)}'
		}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
