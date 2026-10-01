import pytest
from django.urls import reverse
from rest_framework import status

from users.factories import DEFAULT_PASSWORD, UserFactory
from users.models import User

NEW_PASSWORD = "an0ther-Strong-pass"


@pytest.mark.django_db
class TestUserViewSet:
    """Test sign-up and the requesting user's own profile endpoints."""

    def setup_method(self, method):
        """Set up test data."""
        self.user = UserFactory()
        self.url = reverse("users:user", kwargs={"version": "v1"})

    def test_retrieve_own_profile(self, authed_api_client):
        """Test that GET returns the requesting user's profile."""
        client = authed_api_client(self.user)

        response = client.get(self.url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data == {
            "id": self.user.pk,
            "username": self.user.username,
            "email": self.user.email,
            "first_name": self.user.first_name,
            "last_name": self.user.last_name,
        }

    def test_signup_without_token(self, anon_api_client):
        """Test that POST creates a user with a hashed, usable password."""
        payload = {
            "username": "newuser",
            "email": "newuser@example.com",
            "first_name": "New",
            "last_name": "User",
            "password": NEW_PASSWORD,
        }

        response = anon_api_client.post(self.url, payload)

        assert response.status_code == status.HTTP_201_CREATED
        assert "password" not in response.data
        user = User.objects.get(pk=response.data["id"])
        assert user.email == payload["email"]
        assert user.check_password(payload["password"])

    def test_signup_with_weak_password(self, anon_api_client):
        """Test that sign-up rejects a password failing the validators."""
        response = anon_api_client.post(self.url, {"username": "weak", "password": "123"})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "password" in response.data
        assert not User.objects.filter(username="weak").exists()

    def test_update_own_profile(self, authed_api_client):
        """Test that PUT updates the profile but ignores email and password."""
        client = authed_api_client(self.user)
        original_email = self.user.email
        payload = {
            "username": "renamed",
            "first_name": "Re",
            "last_name": "Named",
            "email": "hacked@example.com",
            "password": NEW_PASSWORD,
        }

        response = client.put(self.url, payload)

        assert response.status_code == status.HTTP_200_OK
        self.user.refresh_from_db()
        assert self.user.username == payload["username"]
        assert self.user.first_name == payload["first_name"]
        assert self.user.last_name == payload["last_name"]
        assert self.user.email == original_email
        assert self.user.check_password(DEFAULT_PASSWORD)

    def test_partial_update_own_profile(self, authed_api_client):
        """Test that PATCH updates only the given fields."""
        client = authed_api_client(self.user)
        original_username = self.user.username

        response = client.patch(self.url, {"first_name": "Patched"})

        assert response.status_code == status.HTTP_200_OK
        self.user.refresh_from_db()
        assert self.user.first_name == "Patched"
        assert self.user.username == original_username

    def test_update_with_taken_username(self, authed_api_client):
        """Test that changing to another user's username is rejected."""
        other_user = UserFactory()
        client = authed_api_client(self.user)

        response = client.patch(self.url, {"username": other_user.username})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "username" in response.data

    def test_delete_own_profile(self, authed_api_client):
        """Test that DELETE removes the user's own account."""
        client = authed_api_client(self.user)

        response = client.delete(self.url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not User.objects.filter(pk=self.user.pk).exists()

    def test_per_id_route_does_not_exist(self, authed_api_client):
        """Test that there is no way to address a user by id."""
        client = authed_api_client(self.user)

        response = client.get(f"{self.url}{self.user.pk}/")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.parametrize("method", ["get", "put", "patch", "delete"])
    def test_unauthenticated_requests_are_rejected(self, anon_api_client, method):
        """Test that every profile endpoint requires authentication."""
        response = getattr(anon_api_client, method)(self.url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert User.objects.filter(pk=self.user.pk).exists()


@pytest.mark.django_db
class TestChangePassword:
    """Test the change-password action and token revocation."""

    def setup_method(self, method):
        """Set up test data."""
        self.user = UserFactory()
        self.url = reverse("users:user-change-password", kwargs={"version": "v1"})
        self.user_url = reverse("users:user", kwargs={"version": "v1"})
        self.refresh_url = reverse("users:token_refresh", kwargs={"version": "v1"})
        self.payload = {
            "current_password": DEFAULT_PASSWORD,
            "new_password": NEW_PASSWORD,
        }

    def test_change_password(self, authed_api_client):
        """Test that the password changes and fresh tokens are returned."""
        client = authed_api_client(self.user)

        response = client.post(self.url, self.payload)

        assert response.status_code == status.HTTP_200_OK
        assert {"access", "refresh"} <= response.data.keys()
        self.user.refresh_from_db()
        assert self.user.check_password(NEW_PASSWORD)

    def test_old_tokens_are_revoked(self, api_client):
        """Test that tokens issued before the change stop working."""
        old_access, old_refresh = self.user.jwt, self.user.jwt_refresh
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {old_access}")
        api_client.post(self.url, self.payload)

        response = api_client.get(self.user_url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        api_client.credentials()
        response = api_client.post(self.refresh_url, {"refresh": old_refresh})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_new_tokens_work(self, api_client):
        """Test that the returned tokens authenticate and refresh."""
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.user.jwt}")
        tokens = api_client.post(self.url, self.payload).data

        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        assert api_client.get(self.user_url).status_code == status.HTTP_200_OK

        api_client.credentials()
        response = api_client.post(self.refresh_url, {"refresh": tokens["refresh"]})
        assert response.status_code == status.HTTP_200_OK

    def test_wrong_current_password(self, authed_api_client):
        """Test that an incorrect current password is rejected."""
        client = authed_api_client(self.user)

        response = client.post(
            self.url, {**self.payload, "current_password": "wrong-password"}
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "current_password" in response.data
        self.user.refresh_from_db()
        assert self.user.check_password(DEFAULT_PASSWORD)

    def test_weak_new_password(self, authed_api_client):
        """Test that a new password failing the validators is rejected."""
        client = authed_api_client(self.user)

        response = client.post(self.url, {**self.payload, "new_password": "123"})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "new_password" in response.data
        self.user.refresh_from_db()
        assert self.user.check_password(DEFAULT_PASSWORD)

    def test_unauthenticated_request_is_rejected(self, anon_api_client):
        """Test that changing the password requires authentication."""
        response = anon_api_client.post(self.url, self.payload)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
