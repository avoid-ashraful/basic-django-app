import pytest
from django.urls import reverse
from rest_framework import status

from common.factories import SampleFactory
from common.models import Sample
from users.factories import UserFactory


@pytest.mark.django_db
class TestSampleViewSet:
    """Test CRUD endpoints for Sample."""

    def setup_method(self, method):
        """Set up test data."""
        self.user = UserFactory()
        self.sample = SampleFactory()
        self.list_url = reverse("common:sample-list", kwargs={"version": "v1"})
        self.detail_url = reverse(
            "common:sample-detail", kwargs={"version": "v1", "pk": self.sample.pk}
        )

    def test_list_samples(self, authed_api_client):
        """Test that GET on the list endpoint returns all samples."""
        SampleFactory.create_batch(2)
        client = authed_api_client(self.user)

        response = client.get(self.list_url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 3

    def test_retrieve_sample(self, authed_api_client):
        """Test that GET on the detail endpoint returns the sample."""
        client = authed_api_client(self.user)

        response = client.get(self.detail_url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == self.sample.pk
        assert response.data["name"] == self.sample.name

    def test_create_sample(self, authed_api_client):
        """Test that POST creates a sample."""
        client = authed_api_client(self.user)
        payload = {
            "name": "New sample",
            "description": "A description",
            "status": Sample.Status.PUBLISHED,
            "quantity": 5,
        }

        response = client.post(self.list_url, payload)

        assert response.status_code == status.HTTP_201_CREATED
        sample = Sample.objects.get(pk=response.data["id"])
        assert sample.name == payload["name"]
        assert sample.status == payload["status"]
        assert sample.quantity == payload["quantity"]
        assert sample.is_active is True

    def test_create_sample_with_invalid_data(self, authed_api_client):
        """Test that POST with missing required fields is rejected."""
        client = authed_api_client(self.user)

        response = client.post(self.list_url, {"status": "unknown"})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert {"name", "status"} <= response.data.keys()
        assert Sample.objects.count() == 1

    def test_update_sample(self, authed_api_client):
        """Test that PUT replaces the sample."""
        client = authed_api_client(self.user)
        payload = {
            "name": "Updated sample",
            "description": "Updated description",
            "status": Sample.Status.ARCHIVED,
            "quantity": 42,
            "is_active": False,
        }

        response = client.put(self.detail_url, payload)

        assert response.status_code == status.HTTP_200_OK
        self.sample.refresh_from_db()
        assert self.sample.name == payload["name"]
        assert self.sample.description == payload["description"]
        assert self.sample.status == payload["status"]
        assert self.sample.quantity == payload["quantity"]
        assert self.sample.is_active is False

    def test_partial_update_sample(self, authed_api_client):
        """Test that PATCH updates only the given fields."""
        client = authed_api_client(self.user)
        original_name = self.sample.name

        response = client.patch(self.detail_url, {"quantity": 7})

        assert response.status_code == status.HTTP_200_OK
        self.sample.refresh_from_db()
        assert self.sample.quantity == 7
        assert self.sample.name == original_name

    def test_delete_sample(self, authed_api_client):
        """Test that DELETE removes the sample."""
        client = authed_api_client(self.user)

        response = client.delete(self.detail_url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Sample.objects.filter(pk=self.sample.pk).exists()

    def test_retrieve_missing_sample(self, authed_api_client):
        """Test that GET on a non-existent sample returns 404."""
        client = authed_api_client(self.user)
        url = reverse("common:sample-detail", kwargs={"version": "v1", "pk": 0})

        response = client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.parametrize(
        ("method", "url_name"),
        [
            ("get", "list_url"),
            ("post", "list_url"),
            ("get", "detail_url"),
            ("put", "detail_url"),
            ("patch", "detail_url"),
            ("delete", "detail_url"),
        ],
    )
    def test_unauthenticated_requests_are_rejected(
        self, anon_api_client, method, url_name
    ):
        """Test that every endpoint requires authentication."""
        response = getattr(anon_api_client, method)(getattr(self, url_name))

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert Sample.objects.filter(pk=self.sample.pk).exists()
