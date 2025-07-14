from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.utils import timezone
from .models import User, UserProfile, UserActivityLog
from .serializers import (
	UserRegistrationSerializer, 
	UserWithProfileSerializer,
	UserProfileUpdateSerializer,
	CustomTokenObtainPairSerializer
)


def create_response(success=True, data=None, message="", error=None):
	"""Standard API response format"""
	if success:
		return {"success": True, "data": data, "message": message}
	else:
		return {"success": False, "error": error}


class UserRegistrationView(APIView):
	permission_classes = [permissions.AllowAny]

	def post(self, request):
		serializer = UserRegistrationSerializer(data=request.data)
		if serializer.is_valid():
			user = serializer.save()
			
			# Generate tokens
			refresh = RefreshToken.for_user(user)
			access_token = refresh.access_token
			
			# Log activity
			UserActivityLog.objects.create(
				user=user,
				activity_type='user_registration',
				ip_address=request.META.get('REMOTE_ADDR'),
				user_agent=request.META.get('HTTP_USER_AGENT')
			)
			
			response_data = {
				"user": UserWithProfileSerializer(user).data,
				"token": str(access_token),
				"refresh_token": str(refresh)
			}
			
			return Response(
				create_response(data=response_data, message="User registered successfully"),
				status=status.HTTP_201_CREATED
			)
		
		return Response(
			create_response(success=False, error={
				"code": "VALIDATION_ERROR",
				"message": "Invalid data provided",
				"details": serializer.errors
			}),
			status=status.HTTP_400_BAD_REQUEST
		)


class CustomTokenObtainPairView(TokenObtainPairView):
	serializer_class = CustomTokenObtainPairSerializer
	permission_classes = [permissions.AllowAny]

	def post(self, request, *args, **kwargs):
		serializer = self.get_serializer(data=request.data)
		
		if serializer.is_valid():
			user = serializer.user
			
			# Update last login
			user.last_login = timezone.now()
			user.save()
			
			# Log activity
			UserActivityLog.objects.create(
				user=user,
				activity_type='user_login',
				ip_address=request.META.get('REMOTE_ADDR'),
				user_agent=request.META.get('HTTP_USER_AGENT')
			)
			
			return Response(
				create_response(data=serializer.validated_data, message="Login successful"),
				status=status.HTTP_200_OK
			)
		
		return Response(
			create_response(success=False, error={
				"code": "AUTHENTICATION_ERROR",
				"message": "Invalid credentials",
				"details": serializer.errors
			}),
			status=status.HTTP_401_UNAUTHORIZED
		)


class CustomTokenRefreshView(TokenRefreshView):
	permission_classes = [permissions.AllowAny]

	def post(self, request, *args, **kwargs):
		response = super().post(request, *args, **kwargs)
		if response.status_code == 200:
			return Response(
				create_response(data=response.data, message="Token refreshed successfully"),
				status=status.HTTP_200_OK
			)
		
		return Response(
			create_response(success=False, error={
				"code": "AUTHENTICATION_ERROR",
				"message": "Invalid refresh token",
				"details": response.data
			}),
			status=status.HTTP_401_UNAUTHORIZED
		)


class LogoutView(APIView):
	permission_classes = [permissions.IsAuthenticated]

	def post(self, request):
		try:
			refresh_token = request.data.get("refresh_token")
			if refresh_token:
				token = RefreshToken(refresh_token)
				token.blacklist()
			
			# Log activity
			UserActivityLog.objects.create(
				user=request.user,
				activity_type='user_logout',
				ip_address=request.META.get('REMOTE_ADDR'),
				user_agent=request.META.get('HTTP_USER_AGENT')
			)
			
			return Response(
				create_response(message="Logged out successfully"),
				status=status.HTTP_200_OK
			)
		except Exception as e:
			return Response(
				create_response(success=False, error={
					"code": "PROCESSING_ERROR",
					"message": "Logout failed",
					"details": str(e)
				}),
				status=status.HTTP_400_BAD_REQUEST
			)


class UserProfileView(APIView):
	permission_classes = [permissions.IsAuthenticated]

	def get(self, request):
		"""Get user profile"""
		user_data = UserWithProfileSerializer(request.user).data
		return Response(
			create_response(data=user_data),
			status=status.HTTP_200_OK
		)

	def put(self, request):
		"""Update user profile"""
		try:
			profile = request.user.profile
		except UserProfile.DoesNotExist:
			profile = UserProfile.objects.create(user=request.user)
		
		serializer = UserProfileUpdateSerializer(profile, data=request.data, partial=True)
		if serializer.is_valid():
			serializer.save()
			
			# Log activity
			UserActivityLog.objects.create(
				user=request.user,
				activity_type='profile_update',
				activity_data=request.data,
				ip_address=request.META.get('REMOTE_ADDR'),
				user_agent=request.META.get('HTTP_USER_AGENT')
			)
			
			user_data = UserWithProfileSerializer(request.user).data
			return Response(
				create_response(data=user_data, message="Profile updated successfully"),
				status=status.HTTP_200_OK
			)
		
		return Response(
			create_response(success=False, error={
				"code": "VALIDATION_ERROR",
				"message": "Invalid data provided",
				"details": serializer.errors
			}),
			status=status.HTTP_400_BAD_REQUEST
		)
