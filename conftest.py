import pytest


@pytest.fixture(autouse=True)
def _fast_password_hasher(settings):  # noqa: PT004
    """Use a fast hasher in tests; the default PBKDF2 is intentionally slow."""
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]


@pytest.fixture
def api_client():
    """A Django Rest Framework api test client instance."""
    from rest_framework.test import APIClient

    return APIClient()


@pytest.fixture
def anon_api_client(api_client):
    """An unauthenticated DRF api test client."""
    return api_client


@pytest.fixture
def authed_api_client(api_client):
    """Return a factory that authenticates the api client as a given user."""

    def _api_client_authenticator(user):
        """Attach the user's JWT to the api client and return it."""
        api_client.credentials(HTTP_AUTHORIZATION="Bearer " + user.jwt)
        return api_client

    return _api_client_authenticator
