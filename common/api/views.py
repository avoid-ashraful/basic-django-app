from rest_framework import viewsets

from common.api.serializers import SampleSerializer
from common.models import Sample


class SampleViewSet(viewsets.ModelViewSet):
    """CRUD endpoints for Sample."""

    queryset = Sample.objects.all()
    serializer_class = SampleSerializer
