import pytest
from django.urls import reverse
from rest_framework import status

from common.factories import SampleFactory
from users.factories import UserFactory


@pytest.mark.django_db
class TestAdmin:
    """Test that registered models are reachable in the Django admin."""

    def setup_method(self, method):
        """Set up test data."""
        self.admin_user = UserFactory(is_staff=True, is_superuser=True)
        self.sample = SampleFactory()

    @pytest.mark.parametrize(
        "model",
        ["users_user", "common_sample"],
    )
    def test_changelist_and_add_pages(self, client, model):
        """Test that a superuser can open the changelist and add pages."""
        client.force_login(self.admin_user)

        for view in ("changelist", "add"):
            response = client.get(reverse(f"admin:{model}_{view}"))
            assert response.status_code == status.HTTP_200_OK

    def test_change_pages(self, client):
        """Test that a superuser can open the change page for each model."""
        client.force_login(self.admin_user)

        for url in (
            reverse("admin:users_user_change", args=[self.admin_user.pk]),
            reverse("admin:common_sample_change", args=[self.sample.pk]),
        ):
            response = client.get(url)
            assert response.status_code == status.HTTP_200_OK

    def test_non_staff_user_is_redirected_to_login(self, client):
        """Test that a non-staff user cannot access the admin."""
        client.force_login(UserFactory())

        response = client.get(reverse("admin:common_sample_changelist"))

        assert response.status_code == status.HTTP_302_FOUND
        assert reverse("admin:login") in response.url
