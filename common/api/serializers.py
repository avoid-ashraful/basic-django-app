from rest_framework import serializers

from common.models import Sample


class SampleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sample
        fields = [
            "id",
            "name",
            "description",
            "status",
            "quantity",
            "is_active",
            "created",
            "modified",
        ]
        read_only_fields = ["id", "created", "modified"]
