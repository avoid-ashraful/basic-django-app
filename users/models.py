from django.contrib.auth.models import AbstractUser
from rest_framework_simplejwt.tokens import RefreshToken


class User(AbstractUser):
    """Custom user model; extend with project-specific fields as needed."""

    @property
    def jwt(self):
        """Return a signed access token for this user."""
        return str(RefreshToken.for_user(self).access_token)

    @property
    def jwt_refresh(self):
        """Return a signed refresh token for this user."""
        return str(RefreshToken.for_user(self))
