"""
Serializers for the cart application.

Handles cart display, item addition, and quantity updates
with stock validation.
"""

from rest_framework import serializers

from apps.products.models import Product

from .models import Cart, CartItem


class CartItemSerializer(serializers.ModelSerializer):
    """Serializer for cart items with product details."""

    product_name = serializers.CharField(source="product.name", read_only=True)
    product_slug = serializers.CharField(source="product.slug", read_only=True)
    product_price = serializers.DecimalField(
        source="product.price",
        max_digits=10,
        decimal_places=2,
        read_only=True,
    )
    product_image = serializers.SerializerMethodField()
    vendor_name = serializers.CharField(
        source="product.vendor.store_name", read_only=True
    )
    line_total = serializers.ReadOnlyField()
    is_available = serializers.ReadOnlyField()
    max_quantity = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = [
            "id",
            "product",
            "product_name",
            "product_slug",
            "product_price",
            "product_image",
            "vendor_name",
            "quantity",
            "line_total",
            "is_available",
            "max_quantity",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def get_product_image(self, obj):
        primary = obj.product.primary_image
        if primary:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(primary.image.url)
            return primary.image.url
        return None

    def get_max_quantity(self, obj):
        if obj.product.track_inventory:
            return obj.product.stock_quantity
        return 999


class CartSerializer(serializers.ModelSerializer):
    """Serializer for the complete cart with all items."""

    items = CartItemSerializer(many=True, read_only=True)
    total_items = serializers.ReadOnlyField()
    total_unique_items = serializers.ReadOnlyField()
    subtotal = serializers.ReadOnlyField()

    class Meta:
        model = Cart
        fields = [
            "id",
            "items",
            "total_items",
            "total_unique_items",
            "subtotal",
            "updated_at",
        ]
        read_only_fields = ["id", "updated_at"]


class AddToCartSerializer(serializers.Serializer):
    """Serializer for adding an item to the cart."""

    product_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1, default=1)

    def validate_product_id(self, value):
        try:
            product = Product.objects.get(id=value, status=Product.Status.ACTIVE)
        except Product.DoesNotExist:
            raise serializers.ValidationError("Product not found or unavailable.")
        return value

    def validate(self, attrs):
        product = Product.objects.get(id=attrs["product_id"])
        quantity = attrs["quantity"]

        # Check if vendor is approved
        if not product.vendor.is_approved:
            raise serializers.ValidationError(
                "This product's vendor is not currently active."
            )

        # Check stock availability
        if product.track_inventory:
            # Consider existing quantity in cart
            request = self.context["request"]
            cart, _ = Cart.objects.get_or_create(user=request.user)
            existing_item = cart.items.filter(product=product).first()
            existing_qty = existing_item.quantity if existing_item else 0

            if existing_qty + quantity > product.stock_quantity:
                raise serializers.ValidationError(
                    f"Only {product.stock_quantity - existing_qty} more units available."
                )

        return attrs


class UpdateCartItemSerializer(serializers.Serializer):
    """Serializer for updating cart item quantity."""

    quantity = serializers.IntegerField(min_value=1)

    def validate_quantity(self, value):
        cart_item = self.context.get("cart_item")
        if cart_item and cart_item.product.track_inventory:
            if value > cart_item.product.stock_quantity:
                raise serializers.ValidationError(
                    f"Only {cart_item.product.stock_quantity} units available."
                )
        return value
