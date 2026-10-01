from django.db import models

from common.models import TimeStampedModel


class Tag(TimeStampedModel):
    """Storing tag information."""

    name = models.CharField(max_length=255)
    description = models.TextField()

    def __str__(self):
        """Default string representation."""
        return self.name


class Product(TimeStampedModel):
    """Storing product information."""

    name = models.CharField(max_length=255)
    description = models.TextField()
    tags = models.ManyToManyField(Tag)
    # Unique at the DB level, so concurrent or duplicate imports hit IntegrityError.
    sku = models.CharField(max_length=64, unique=True, null=True, blank=True)
    # Decremented by purchases under a row lock (select_for_update).
    stock = models.PositiveIntegerField(default=0)
    # Incremented with an F() expression, which is race-free without a transaction.
    view_count = models.PositiveIntegerField(default=0)
    # Bumped on every update for optimistic locking.
    version = models.PositiveIntegerField(default=1)

    def __str__(self):
        """Default string representation."""
        return self.name


class ProductActivity(TimeStampedModel):
    """Audit log written in the same transaction as the change it records."""

    class Action(models.TextChoices):
        CREATED = "created", "Created"
        UPDATED = "updated", "Updated"
        PURCHASED = "purchased", "Purchased"
        IMPORTED = "imported", "Imported"

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="activities"
    )
    action = models.CharField(max_length=20, choices=Action.choices)
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        """Default string representation."""
        return f"{self.product_id} {self.action}"
