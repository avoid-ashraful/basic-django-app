from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.utils import get_md5_hash_password

from users.models import User


class UserSignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True, validators=[validate_password], style={"input_type": "password"}
    )

    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "password"]
        read_only_fields = ["id"]

    def create(self, validated_data):
        """Create the user with a properly hashed password."""
        return User.objects.create_user(**validated_data)


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name"]
        read_only_fields = ["id", "email"]


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(
        write_only=True, style={"input_type": "password"}
    )
    new_password = serializers.CharField(
        write_only=True, style={"input_type": "password"}
    )

    def validate_current_password(self, value):
        """Ensure the given current password matches the user's password."""
        if not self.instance.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def validate_new_password(self, value):
        """Run Django's password validators against the new password."""
        validate_password(value, user=self.instance)
        return value

    def update(self, instance, validated_data):
        """Set and save the new hashed password."""
        instance.set_password(validated_data["new_password"])
        instance.save(update_fields=["password"])
        return instance


class RevocableTokenRefreshSerializer(TokenRefreshSerializer):
    """Reject refresh tokens issued before the user's last password change."""

    def validate(self, attrs):
        """Reject the refresh token if the password changed since it was issued."""
        token = self.token_class(attrs["refresh"])
        user = User.objects.filter(pk=token.get(api_settings.USER_ID_CLAIM)).first()
        if user and token.get(api_settings.REVOKE_TOKEN_CLAIM) != get_md5_hash_password(
            user.password
        ):
            raise AuthenticationFailed(
                "The user's password has been changed.", code="password_changed"
            )
        return super().validate(attrs)
