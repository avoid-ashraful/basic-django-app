from rest_framework import mixins, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from users.api.serializers import (
    ChangePasswordSerializer,
    UserProfileSerializer,
    UserSignupSerializer,
)


class UserViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """Sign-up plus retrieve, update and delete of the requesting user's own profile."""

    serializer_class = UserProfileSerializer

    def get_permissions(self):
        """Allow anyone to sign up; require authentication for everything else."""
        if self.action == "create":
            return [AllowAny()]
        return super().get_permissions()

    def get_serializer_class(self):
        """Return the serializer that matches the current action."""
        if self.action == "create":
            return UserSignupSerializer
        if self.action == "change_password":
            return ChangePasswordSerializer
        return super().get_serializer_class()

    def get_object(self):
        """Return the requesting user; users can only act on themselves."""
        return self.request.user

    def change_password(self, request, *args, **kwargs):
        """Change the password, revoke old tokens and return fresh ones."""
        user = self.get_object()
        serializer = self.get_serializer(user, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"access": user.jwt, "refresh": user.jwt_refresh})
