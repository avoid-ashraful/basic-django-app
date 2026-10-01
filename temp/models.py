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

    def __str__(self):
        """Default string representation."""
        return self.name
