from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

from users.api.views import UserViewSet

app_name = "users"

# The user endpoint is the requesting user's own profile, so standard actions are
# mapped onto a single URL instead of the router's list and <pk> routes.
user = UserViewSet.as_view(
    {
        "get": "retrieve",
        "post": "create",
        "put": "update",
        "patch": "partial_update",
        "delete": "destroy",
    }
)
change_password = UserViewSet.as_view({"post": "change_password"})

urlpatterns = [
    path("auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("auth/token/verify/", TokenVerifyView.as_view(), name="token_verify"),
    path("users/", user, name="user"),
    path("users/change-password/", change_password, name="user-change-password"),
]
