from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import authenticate
from .models import User, UserProfile


class UserRegistrationSerializer(serializers.ModelSerializer):
	password = serializers.CharField(write_only=True, min_length=8)
	nickname = serializers.CharField(max_length=50, required=False)

	class Meta:
		model = User
		fields = ['username', 'email', 'password', 'nickname']

	def validate_email(self, value):
		if User.objects.filter(email=value).exists():
			raise serializers.ValidationError("Email already exists")
		return value

	def validate_username(self, value):
		if User.objects.filter(username=value).exists():
			raise serializers.ValidationError("Username already exists")
		return value

	def create(self, validated_data):
		nickname = validated_data.pop('nickname', '')
		password = validated_data.pop('password')
		user = User.objects.create_user(**validated_data)
		user.set_password(password)
		user.nickname = nickname
		user.save()
		
		# Create user profile
		UserProfile.objects.create(user=user)
		
		return user


class UserSerializer(serializers.ModelSerializer):
	class Meta:
		model = User
		fields = ['id', 'username', 'email', 'nickname', 'date_joined']
		read_only_fields = ['id', 'date_joined']


class UserProfileSerializer(serializers.ModelSerializer):
	class Meta:
		model = UserProfile
		fields = ['date_of_birth', 'gender', 'height', 'weight', 'daily_calorie_goal']


class UserProfileUpdateSerializer(serializers.ModelSerializer):
	nickname = serializers.CharField(source='user.nickname', max_length=50, required=False)

	class Meta:
		model = UserProfile
		fields = ['nickname', 'date_of_birth', 'gender', 'height', 'weight', 'daily_calorie_goal']

	def update(self, instance, validated_data):
		user_data = validated_data.pop('user', {})
		if 'nickname' in user_data:
			instance.user.nickname = user_data['nickname']
			instance.user.save()

		return super().update(instance, validated_data)


class UserWithProfileSerializer(serializers.ModelSerializer):
	profile = UserProfileSerializer(read_only=True)

	class Meta:
		model = User
		fields = ['id', 'username', 'email', 'nickname', 'profile']


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
	@classmethod
	def get_token(cls, user):
		token = super().get_token(user)
		token['username'] = user.username
		token['email'] = user.email
		return token

	def validate(self, attrs):
		data = super().validate(attrs)
		
		# Add user data to response
		data['user'] = UserWithProfileSerializer(self.user).data
		
		return data