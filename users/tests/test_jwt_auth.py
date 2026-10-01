import pytest
from django.urls import reverse
from rest_framework import status

from users.factories import DEFAULT_PASSWORD, UserFactory


@pytest.mark.django_db
class TestJWTAuth:
    """Test JWT token obtain, refresh, verify and authentication."""

    def setup_method(self, method):
        """Set up test data."""
        self.user = UserFactory()
        self.token_url = reverse("users:token_obtain_pair", kwargs={"version": "v1"})
        self.refresh_url = reverse("users:token_refresh", kwargs={"version": "v1"})
        self.verify_url = reverse("users:token_verify", kwargs={"version": "v1"})
        self.protected_url = reverse("common:sample-list", kwargs={"version": "v1"})

    def test_obtain_token_with_valid_credentials(self, anon_api_client):
        """Test that valid credentials return an access and refresh token."""
        response = anon_api_client.post(
            self.token_url,
            {"username": self.user.username, "password": DEFAULT_PASSWORD},
        )

        assert response.status_code == status.HTTP_200_OK
        assert {"access", "refresh"} <= response.data.keys()

    def test_obtain_token_with_invalid_credentials(self, anon_api_client):
        """Test that a wrong password is rejected."""
        response = anon_api_client.post(
            self.token_url,
            {"username": self.user.username, "password": "wrong-password"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_obtain_token_for_inactive_user(self, anon_api_client):
        """Test that an inactive user cannot obtain a token."""
        user = UserFactory(is_active=False)
        response = anon_api_client.post(
            self.token_url,
            {"username": user.username, "password": DEFAULT_PASSWORD},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_refresh_token(self, anon_api_client):
        """Test that a refresh token returns a new access token."""
        response = anon_api_client.post(
            self.refresh_url, {"refresh": self.user.jwt_refresh}
        )

        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data

    def test_verify_token(self, anon_api_client):
        """Test that a valid access token verifies."""
        response = anon_api_client.post(self.verify_url, {"token": self.user.jwt})

        assert response.status_code == status.HTTP_200_OK

    def test_protected_endpoint_with_token(self, authed_api_client):
        """Test that a valid access token grants access."""
        client = authed_api_client(self.user)
        response = client.get(self.protected_url)

        assert response.status_code == status.HTTP_200_OK

    def test_protected_endpoint_without_token(self, anon_api_client):
        """Test that a missing token is rejected."""
        response = anon_api_client.get(self.protected_url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_protected_endpoint_with_invalid_token(self, api_client):
        """Test that a malformed token is rejected."""
        api_client.credentials(HTTP_AUTHORIZATION="Bearer invalid.token.value")
        response = api_client.get(self.protected_url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
