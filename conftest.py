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
    return api_client


@pytest.fixture
def authed_api_client(api_client):
    def _api_client_authenticator(user):
        api_client.credentials(HTTP_AUTHORIZATION="Bearer " + user.jwt)
        return api_client

    return _api_client_authenticator
