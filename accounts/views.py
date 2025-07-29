from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.utils import timezone
import logging
from .models import (
    User,
    UserProfile,
    UserActivityLog,
    EmailVerificationToken,
    PasswordResetToken,
)
from .serializers import (
    UserRegistrationSerializer,
    UserWithProfileSerializer,
    UserProfileUpdateSerializer,
    CustomTokenObtainPairSerializer,
)
from .email_service import send_verification_email, send_password_reset_email
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password

# Get logger for this module
logger = logging.getLogger("accounts")


def create_response(success=True, data=None, message="", error=None):
    """Standard API response format"""
    if success:
        return {"success": True, "data": data, "message": message}
    else:
        return {"success": False, "error": error}


class UserRegistrationView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        logger.info(
            f"User registration attempt for username: {request.data.get('username', 'N/A')}"
        )

        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            logger.info(
                f"User registered successfully: {user.username} (ID: {user.id})"
            )

            # Create email verification token
            verification_token = EmailVerificationToken.objects.create(user=user)

            # Send verification email
            email_sent = send_verification_email(user, verification_token.token)

            # Log activity
            UserActivityLog.objects.create(
                user=user,
                activity_type="user_registration",
                activity_data={"email_sent": email_sent},
                ip_address=request.META.get("REMOTE_ADDR"),
                user_agent=request.META.get("HTTP_USER_AGENT"),
            )

            response_data = {
                "user": UserWithProfileSerializer(user).data,
                "message": "Registration successful. Please check your email to verify your account.",
                "email_sent": email_sent,
            }

            return Response(
                create_response(
                    data=response_data,
                    message="User registered successfully. Email verification required.",
                ),
                status=status.HTTP_201_CREATED,
            )

        logger.warning(f"User registration failed: {serializer.errors}")
        return Response(
            create_response(
                success=False,
                error={
                    "code": "VALIDATION_ERROR",
                    "message": "Invalid data provided",
                    "details": serializer.errors,
                },
            ),
            status=status.HTTP_400_BAD_REQUEST,
        )


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        username = request.data.get("username", "N/A")
        logger.info(f"Login attempt for username: {username}")

        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            user = serializer.user
            logger.info(f"User logged in successfully: {user.username} (ID: {user.id})")

            # Update last login
            user.last_login = timezone.now()
            user.save()

            # Log activity
            UserActivityLog.objects.create(
                user=user,
                activity_type="user_login",
                ip_address=request.META.get("REMOTE_ADDR"),
                user_agent=request.META.get("HTTP_USER_AGENT"),
            )

            return Response(
                create_response(
                    data=serializer.validated_data, message="Login successful"
                ),
                status=status.HTTP_200_OK,
            )

        logger.warning(
            f"Login failed for username: {username}, errors: {serializer.errors}"
        )
        return Response(
            create_response(
                success=False,
                error={
                    "code": "AUTHENTICATION_ERROR",
                    "message": "Invalid credentials",
                    "details": serializer.errors,
                },
            ),
            status=status.HTTP_401_UNAUTHORIZED,
        )


class CustomTokenRefreshView(TokenRefreshView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            return Response(
                create_response(
                    data=response.data, message="Token refreshed successfully"
                ),
                status=status.HTTP_200_OK,
            )

        return Response(
            create_response(
                success=False,
                error={
                    "code": "AUTHENTICATION_ERROR",
                    "message": "Invalid refresh token",
                    "details": response.data,
                },
            ),
            status=status.HTTP_401_UNAUTHORIZED,
        )


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        logger.info(
            f"Logout attempt for user: {request.user.username if request.user.is_authenticated else 'Anonymous'}"
        )

        try:
            refresh_token = request.data.get("refresh_token")
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
                logger.debug(
                    f"Refresh token blacklisted for user: {request.user.username}"
                )

            # Log activity
            UserActivityLog.objects.create(
                user=request.user,
                activity_type="user_logout",
                ip_address=request.META.get("REMOTE_ADDR"),
                user_agent=request.META.get("HTTP_USER_AGENT"),
            )

            logger.info(f"User logged out successfully: {request.user.username}")
            return Response(
                create_response(message="Logged out successfully"),
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.error(f"Logout failed for user {request.user.username}: {str(e)}")
            return Response(
                create_response(
                    success=False,
                    error={
                        "code": "PROCESSING_ERROR",
                        "message": "Logout failed",
                        "details": str(e),
                    },
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )


class UserProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get user profile"""
        logger.debug(f"Profile view requested by user: {request.user.username}")
        user_data = UserWithProfileSerializer(request.user).data
        return Response(create_response(data=user_data), status=status.HTTP_200_OK)

    def put(self, request):
        """Update user profile"""
        logger.info(f"Profile update attempt by user: {request.user.username}")

        try:
            profile = request.user.profile
        except UserProfile.DoesNotExist:
            logger.info(f"Creating new profile for user: {request.user.username}")
            profile = UserProfile.objects.create(user=request.user)

        serializer = UserProfileUpdateSerializer(
            profile, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            logger.info(
                f"Profile updated successfully for user: {request.user.username}"
            )

            # Log activity
            UserActivityLog.objects.create(
                user=request.user,
                activity_type="profile_update",
                activity_data=request.data,
                ip_address=request.META.get("REMOTE_ADDR"),
                user_agent=request.META.get("HTTP_USER_AGENT"),
            )

            user_data = UserWithProfileSerializer(request.user).data
            return Response(
                create_response(data=user_data, message="Profile updated successfully"),
                status=status.HTTP_200_OK,
            )

        logger.warning(
            f"Profile update failed for user {request.user.username}: {serializer.errors}"
        )
        return Response(
            create_response(
                success=False,
                error={
                    "code": "VALIDATION_ERROR",
                    "message": "Invalid data provided",
                    "details": serializer.errors,
                },
            ),
            status=status.HTTP_400_BAD_REQUEST,
        )


class EmailVerificationView(APIView):
    """Handle email verification"""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        token = request.data.get("token")
        if not token:
            return Response(
                create_response(
                    success=False,
                    error={
                        "code": "MISSING_TOKEN",
                        "message": "Verification token is required",
                    },
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            verification_token = EmailVerificationToken.objects.get(
                token=token, is_used=False
            )

            if verification_token.is_expired():
                return Response(
                    create_response(
                        success=False,
                        error={
                            "code": "TOKEN_EXPIRED",
                            "message": "Verification token has expired",
                        },
                    ),
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Mark user as verified
            user = verification_token.user
            user.is_email_verified = True
            user.save()

            # Mark token as used
            verification_token.is_used = True
            verification_token.save()

            # Generate JWT tokens for auto-login
            refresh = RefreshToken.for_user(user)
            access_token = refresh.access_token

            # Log activity
            UserActivityLog.objects.create(
                user=user,
                activity_type="email_verification",
                ip_address=request.META.get("REMOTE_ADDR"),
                user_agent=request.META.get("HTTP_USER_AGENT"),
            )

            logger.info(f"Email verified for user: {user.username}")

            response_data = {
                "user": UserWithProfileSerializer(user).data,
                "token": str(access_token),
                "refresh_token": str(refresh),
            }

            return Response(
                create_response(
                    data=response_data, message="Email verified successfully"
                ),
                status=status.HTTP_200_OK,
            )

        except EmailVerificationToken.DoesNotExist:
            return Response(
                create_response(
                    success=False,
                    error={
                        "code": "INVALID_TOKEN",
                        "message": "Invalid verification token",
                    },
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )


class ResendVerificationEmailView(APIView):
    """Resend verification email"""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get("email")
        if not email:
            return Response(
                create_response(
                    success=False,
                    error={
                        "code": "MISSING_EMAIL",
                        "message": "Email is required",
                    },
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = User.objects.get(email=email)

            if user.is_email_verified:
                return Response(
                    create_response(
                        success=False,
                        error={
                            "code": "ALREADY_VERIFIED",
                            "message": "Email is already verified",
                        },
                    ),
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Create new verification token
            verification_token = EmailVerificationToken.objects.create(user=user)

            # Send verification email
            email_sent = send_verification_email(user, verification_token.token)

            logger.info(f"Verification email resent to: {email}")

            return Response(
                create_response(
                    data={"email_sent": email_sent},
                    message="Verification email sent successfully",
                ),
                status=status.HTTP_200_OK,
            )

        except User.DoesNotExist:
            # Don't reveal if email exists or not for security
            return Response(
                create_response(
                    message="If the email exists, a verification email has been sent"
                ),
                status=status.HTTP_200_OK,
            )


class PasswordResetRequestView(APIView):
    """Request password reset"""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get("email")
        if not email:
            return Response(
                create_response(
                    success=False,
                    error={
                        "code": "MISSING_EMAIL",
                        "message": "Email is required",
                    },
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = User.objects.get(email=email)

            # Create password reset token
            reset_token = PasswordResetToken.objects.create(user=user)

            # Send password reset email
            email_sent = send_password_reset_email(user, reset_token.token)

            # Log activity
            UserActivityLog.objects.create(
                user=user,
                activity_type="password_reset_request",
                activity_data={"email_sent": email_sent},
                ip_address=request.META.get("REMOTE_ADDR"),
                user_agent=request.META.get("HTTP_USER_AGENT"),
            )

            logger.info(f"Password reset requested for: {email}")

        except User.DoesNotExist:
            # Don't reveal if email exists or not for security
            logger.info(f"Password reset requested for non-existent email: {email}")

        # Always return success to avoid email enumeration
        return Response(
            create_response(
                message="If the email exists, a password reset link has been sent"
            ),
            status=status.HTTP_200_OK,
        )


class PasswordResetConfirmView(APIView):
    """Confirm password reset with new password"""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        token = request.data.get("token")
        new_password = request.data.get("password")

        if not token or not new_password:
            return Response(
                create_response(
                    success=False,
                    error={
                        "code": "MISSING_DATA",
                        "message": "Token and new password are required",
                    },
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            reset_token = PasswordResetToken.objects.get(token=token, is_used=False)

            if reset_token.is_expired():
                return Response(
                    create_response(
                        success=False,
                        error={
                            "code": "TOKEN_EXPIRED",
                            "message": "Password reset token has expired",
                        },
                    ),
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Update user password
            user = reset_token.user
            user.password = make_password(new_password)
            user.save()

            # Mark token as used
            reset_token.is_used = True
            reset_token.save()

            # Log activity
            UserActivityLog.objects.create(
                user=user,
                activity_type="password_reset_confirm",
                ip_address=request.META.get("REMOTE_ADDR"),
                user_agent=request.META.get("HTTP_USER_AGENT"),
            )

            logger.info(f"Password reset confirmed for user: {user.username}")

            return Response(
                create_response(message="Password reset successfully"),
                status=status.HTTP_200_OK,
            )

        except PasswordResetToken.DoesNotExist:
            return Response(
                create_response(
                    success=False,
                    error={
                        "code": "INVALID_TOKEN",
                        "message": "Invalid or expired password reset token",
                    },
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )
