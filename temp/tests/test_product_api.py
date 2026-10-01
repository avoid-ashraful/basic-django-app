import pytest
from django.urls import reverse
from rest_framework import status

from temp.factories import ProductFactory, TagFactory
from users.factories import UserFactory


@pytest.mark.django_db
class TestProductViewSet:
    """Test CRUD endpoints for Product."""

    def setup_method(self, method):
        """Set up test data."""
        self.user = UserFactory()
        self.list_url = reverse("temp:product-list", kwargs={"version": "v1"})

    def test_list_samples(self, authed_api_client):

        ProductFactory.create_batch(size=5)
        client = authed_api_client(self.user)
        response = client.get(self.list_url)
        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.parametrize("num_tags", [1, 2, 3])
    def test_create_samples(self, authed_api_client, num_tags):
        client = authed_api_client(self.user)
        tags = TagFactory.create_batch(size=num_tags)
        response = client.post(
            self.list_url,
            {"name": "Test 1", "description": "Test 1", "tags": [tag.id for tag in tags]},
        )
        if num_tags in (1, 2):
            assert response.status_code == status.HTTP_201_CREATED
        else:
            assert response.status_code == status.HTTP_400_BAD_REQUEST
