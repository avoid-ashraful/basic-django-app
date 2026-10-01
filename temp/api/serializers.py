from rest_framework import serializers

from temp.models import Product, Tag


class TagSerializer(serializers.ModelSerializer):
    """Serializer class for Tag model"""

    class Meta:
        model = Tag
        fields = [
            "id",
            "name",
            "description",
        ]
        read_only_fields = fields


class ProductSerializer(serializers.ModelSerializer):
    """Serializer class for Product model"""

    tags = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Tag.objects.all(), required=False
    )

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "description",
            "tags",
            "sku",
            "stock",
            "view_count",
            "version",
        ]
        read_only_fields = ["view_count", "version"]

    def to_representation(self, instance):
        """Return tags as full objects instead of ids."""
        data = super().to_representation(instance)
        data["tags"] = TagSerializer(instance.tags.all(), many=True).data
        return data
