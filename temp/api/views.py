from typing import Any

from rest_framework import viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response

from temp.api.serializers import ProductSerializer
from temp.models import Product


class ProductViewSet(viewsets.ModelViewSet):
    """CRUD endpoints for Product model."""

    queryset = Product.objects.all()
    serializer_class = ProductSerializer

    def get_queryset(self):
        return super().get_queryset().prefetch_related("tags")

    def _validate_tags(self, tags):
        if len(tags) > 2 :
            raise ValidationError("Too many tags")

    def create(self, request: Request, *args, **kwargs):
        self._validate_tags(request.data.get("tags", []))
        return super().create(request, *args, **kwargs)

    def partial_update(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        self._validate_tags(request.data.get("tags", []))
        return super().partial_update(request, *args, **kwargs)
