"""
Serializers for the wishlist application.

Handles wishlist display, item addition, and management.
"""

from rest_framework import serializers

from apps.products.models import Product

from .models import Wishlist, WishlistItem


class WishlistItemSerializer(serializers.ModelSerializer):
    """Serializer for wishlist items with product details."""

    product_name = serializers.CharField(source="product.name", read_only=True)
    product_slug = serializers.CharField(source="product.slug", read_only=True)
    current_price = serializers.DecimalField(
        source="product.price",
        max_digits=10,
        decimal_places=2,
        read_only=True,
    )
    product_image = serializers.SerializerMethodField()
    has_price_drop = serializers.ReadOnlyField()
    price_difference = serializers.ReadOnlyField()
    is_in_stock = serializers.ReadOnlyField()
    vendor_name = serializers.CharField(
        source="product.vendor.store_name", read_only=True
    )

    class Meta:
        model = WishlistItem
        fields = [
            "id",
            "product",
            "product_name",
            "product_slug",
            "product_image",
            "vendor_name",
            "price_when_added",
            "current_price",
            "has_price_drop",
            "price_difference",
            "is_in_stock",
            "note",
            "added_at",
        ]
        read_only_fields = ["id", "price_when_added", "added_at"]

    def get_product_image(self, obj):
        primary = obj.product.primary_image
        if primary:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(primary.image.url)
            return primary.image.url
        return None


class WishlistSerializer(serializers.ModelSerializer):
    """Serializer for a wishlist with its items."""

    items = WishlistItemSerializer(many=True, read_only=True)
    item_count = serializers.ReadOnlyField()

    class Meta:
        model = Wishlist
        fields = [
            "id",
            "name",
            "is_default",
            "is_public",
            "item_count",
            "items",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "is_default", "created_at", "updated_at"]


class WishlistListSerializer(serializers.ModelSerializer):
    """Simplified serializer for listing wishlists (without items)."""

    item_count = serializers.ReadOnlyField()

    class Meta:
        model = Wishlist
        fields = [
            "id",
            "name",
            "is_default",
            "is_public",
            "item_count",
            "updated_at",
        ]


class AddToWishlistSerializer(serializers.Serializer):
    """Serializer for adding a product to a wishlist."""

    product_id = serializers.UUIDField()
    wishlist_id = serializers.UUIDField(required=False)
    note = serializers.CharField(max_length=500, required=False, default="")

    def validate_product_id(self, value):
        try:
            Product.objects.get(id=value, status=Product.Status.ACTIVE)
        except Product.DoesNotExist:
            raise serializers.ValidationError("Product not found or unavailable.")
        return value

    def validate_wishlist_id(self, value):
        if value:
            user = self.context["request"].user
            if not Wishlist.objects.filter(id=value, user=user).exists():
                raise serializers.ValidationError("Wishlist not found.")
        return value
