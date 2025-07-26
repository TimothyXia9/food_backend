from django.urls import path
from .views import (
    UserRegistrationView,
    CustomTokenObtainPairView,
    CustomTokenRefreshView,
    LogoutView,
    UserProfileView,
)

urlpatterns = [
    # Authentication endpoints
    path("register", UserRegistrationView.as_view(), name="user-register"),
    path("login", CustomTokenObtainPairView.as_view(), name="user-login"),
    path("refresh", CustomTokenRefreshView.as_view(), name="token-refresh"),
    path("logout", LogoutView.as_view(), name="user-logout"),
    # User profile endpoints
    path("profile", UserProfileView.as_view(), name="user-profile"),
    path("user/", UserProfileView.as_view(), name="current-user"),
]
