from unittest import mock

import pytest
from django.db import IntegrityError, transaction
from django.urls import reverse
from rest_framework import status

from temp.factories import ProductFactory
from temp.models import Product, ProductActivity
from users.factories import UserFactory


@pytest.mark.django_db
class TestProductTransactions:
    """Test each transaction pattern demonstrated in ProductViewSet."""

    def setup_method(self, method):
        """Set up test data."""
        self.user = UserFactory()
        self.product = ProductFactory(name="Original", stock=5)
        self.list_url = reverse("temp:product-list", kwargs={"version": "v1"})
        self.detail_url = reverse(
            "temp:product-detail", kwargs={"version": "v1", "pk": self.product.pk}
        )
        self.purchase_url = reverse(
            "temp:product-purchase", kwargs={"version": "v1", "pk": self.product.pk}
        )
        self.import_url = reverse(
            "temp:product-import-products", kwargs={"version": "v1"}
        )

    # 1. F() expression
    def test_retrieve_increments_view_count(self, authed_api_client):
        """Test that each retrieve bumps view_count in the database."""
        client = authed_api_client(self.user)

        client.get(self.detail_url)
        response = client.get(self.detail_url)

        assert response.data["view_count"] == 2

    # 2. atomic + on_commit
    def test_create_writes_activity_and_notifies_after_commit(
        self, authed_api_client, django_capture_on_commit_callbacks
    ):
        """Test that create logs activity and only notifies once committed."""
        client = authed_api_client(self.user)

        with mock.patch("temp.api.views.notify_warehouse") as notify:
            with django_capture_on_commit_callbacks(execute=True) as callbacks:
                response = client.post(self.list_url, {"name": "New", "description": "d"})

        assert response.status_code == status.HTTP_201_CREATED
        product_id = response.data["id"]
        assert ProductActivity.objects.filter(
            product_id=product_id, action=ProductActivity.Action.CREATED
        ).exists()
        assert len(callbacks) == 1
        notify.assert_called_once_with(product_id, "created")

    def test_create_rolls_back_product_when_activity_fails(self, authed_api_client):
        """Test that a failing activity insert also undoes the product insert."""
        client = authed_api_client(self.user)

        with mock.patch.object(
            ProductActivity.objects, "create", side_effect=IntegrityError("boom")
        ):
            with pytest.raises(IntegrityError):
                client.post(self.list_url, {"name": "Doomed", "description": "d"})

        assert not Product.objects.filter(name="Doomed").exists()

    # 3. set_rollback dry run
    def test_dry_run_previews_without_saving(
        self, authed_api_client, django_capture_on_commit_callbacks
    ):
        """Test that ?dry_run=true returns the new data but rolls everything back."""
        client = authed_api_client(self.user)

        with django_capture_on_commit_callbacks() as callbacks:
            response = client.patch(
                f"{self.detail_url}?dry_run=true", {"name": "Preview"}
            )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == "Preview"
        self.product.refresh_from_db()
        assert self.product.name == "Original"
        assert self.product.version == 1
        assert not ProductActivity.objects.filter(product=self.product).exists()
        assert callbacks == []

    # 4. Optimistic locking
    def test_update_with_current_version_succeeds(self, authed_api_client):
        """Test that an update based on the latest version bumps the version."""
        client = authed_api_client(self.user)

        response = client.patch(self.detail_url, {"name": "Edited", "version": 1})

        assert response.status_code == status.HTTP_200_OK
        assert response.data["version"] == 2
        self.product.refresh_from_db()
        assert self.product.name == "Edited"
        assert self.product.version == 2

    def test_update_with_stale_version_conflicts(self, authed_api_client):
        """Test that an update based on an old version is rejected with 409."""
        Product.objects.filter(pk=self.product.pk).update(version=2)
        client = authed_api_client(self.user)

        response = client.patch(self.detail_url, {"name": "Lost update", "version": 1})

        assert response.status_code == status.HTTP_409_CONFLICT
        self.product.refresh_from_db()
        assert self.product.name == "Original"

    # 5. select_for_update + durable
    def test_purchase_decrements_stock(
        self, authed_api_client, django_capture_on_commit_callbacks
    ):
        """Test that a purchase lowers stock, logs it and notifies after commit."""
        client = authed_api_client(self.user)

        with django_capture_on_commit_callbacks() as callbacks:
            response = client.post(self.purchase_url, {"quantity": 2})

        assert response.status_code == status.HTTP_200_OK
        assert response.data["stock"] == 3
        self.product.refresh_from_db()
        assert self.product.stock == 3
        assert ProductActivity.objects.filter(
            product=self.product, action=ProductActivity.Action.PURCHASED
        ).exists()
        assert len(callbacks) == 1

    @pytest.mark.parametrize("quantity", [6, 0, "abc"])
    def test_purchase_rejects_invalid_quantity(self, authed_api_client, quantity):
        """Test that out-of-stock or invalid quantities change nothing."""
        client = authed_api_client(self.user)

        response = client.post(self.purchase_url, {"quantity": quantity})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        self.product.refresh_from_db()
        assert self.product.stock == 5

    def test_purchase_refuses_to_nest_in_outer_transaction(self, authed_api_client):
        """Test that durable=True raises when called inside another atomic block."""
        client = authed_api_client(self.user)

        with pytest.raises(RuntimeError, match="durable"):
            with transaction.atomic():
                client.post(self.purchase_url, {"quantity": 1})

    # 6. Savepoints
    def test_import_keeps_good_rows_and_reports_duplicates(self, authed_api_client):
        """Test that a duplicate sku only rolls back its own row."""
        client = authed_api_client(self.user)
        rows = [
            {"name": "A", "sku": "SKU-1"},
            {"name": "B", "sku": "SKU-1"},
            {"name": "C", "sku": "SKU-2"},
        ]

        response = client.post(self.import_url, rows)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["created"]) == 2
        assert response.data["errors"] == [{"row": 1, "error": "Duplicate sku."}]
        assert set(
            Product.objects.filter(sku__isnull=False).values_list("name", flat=True)
        ) == {
            "A",
            "C",
        }
        assert (
            ProductActivity.objects.filter(action=ProductActivity.Action.IMPORTED).count()
            == 2
        )
