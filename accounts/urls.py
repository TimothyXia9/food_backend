from django.urls import path
from .views import (
    UserRegistrationView,
    CustomTokenObtainPairView,
    CustomTokenRefreshView,
    LogoutView,
    UserProfileView,
    EmailVerificationView,
    ResendVerificationEmailView,
    PasswordResetRequestView,
    PasswordResetConfirmView,
)

urlpatterns = [
    # Authentication endpoints
    path("register", UserRegistrationView.as_view(), name="user-register"),
    path("login", CustomTokenObtainPairView.as_view(), name="user-login"),
    path("refresh", CustomTokenRefreshView.as_view(), name="token-refresh"),
    path("logout", LogoutView.as_view(), name="user-logout"),
    # Email verification endpoints
    path("verify-email", EmailVerificationView.as_view(), name="email-verify"),
    path("resend-verification", ResendVerificationEmailView.as_view(), name="resend-verification"),
    # Password reset endpoints
    path("password-reset", PasswordResetRequestView.as_view(), name="password-reset-request"),
    path("password-reset-confirm", PasswordResetConfirmView.as_view(), name="password-reset-confirm"),
    # User profile endpoints
    path("profile", UserProfileView.as_view(), name="user-profile"),
    path("user/", UserProfileView.as_view(), name="current-user"),
]
