"""
Serializers for the orders application.

Handles order creation from cart, order listing, detail views,
and vendor-side order management.
"""

from django.db import transaction
from rest_framework import serializers

from apps.accounts.serializers import UserSerializer
from apps.products.serializers import ProductListSerializer

from .models import Order, OrderItem


class OrderItemSerializer(serializers.ModelSerializer):
    """Serializer for order line items."""

    total_price = serializers.ReadOnlyField()
    product_slug = serializers.CharField(source="product.slug", read_only=True)
    product_image = serializers.SerializerMethodField()
    vendor_name = serializers.CharField(source="vendor.store_name", read_only=True)

    class Meta:
        model = OrderItem
        fields = [
            "id",
            "product",
            "product_name",
            "product_slug",
            "product_sku",
            "product_image",
            "vendor_name",
            "unit_price",
            "quantity",
            "total_price",
            "is_fulfilled",
            "fulfilled_at",
        ]
        read_only_fields = [
            "id",
            "product_name",
            "product_sku",
            "unit_price",
            "is_fulfilled",
            "fulfilled_at",
        ]

    def get_product_image(self, obj):
        primary = obj.product.primary_image
        if primary:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(primary.image.url)
            return primary.image.url
        return None


class OrderListSerializer(serializers.ModelSerializer):
    """Simplified serializer for order listing."""

    item_count = serializers.SerializerMethodField()
    first_item_image = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id",
            "order_number",
            "status",
            "payment_status",
            "total_amount",
            "item_count",
            "first_item_image",
            "created_at",
        ]

    def get_item_count(self, obj):
        return obj.items.count()

    def get_first_item_image(self, obj):
        first_item = obj.items.first()
        if first_item:
            primary = first_item.product.primary_image
            if primary:
                request = self.context.get("request")
                if request:
                    return request.build_absolute_uri(primary.image.url)
                return primary.image.url
        return None


class OrderDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for a single order."""

    customer = UserSerializer(read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)
    can_cancel = serializers.ReadOnlyField()

    class Meta:
        model = Order
        fields = [
            "id",
            "order_number",
            "customer",
            "status",
            "subtotal",
            "shipping_cost",
            "tax_amount",
            "discount_amount",
            "total_amount",
            "payment_status",
            "paid_at",
            "shipping_full_name",
            "shipping_phone",
            "shipping_address_line1",
            "shipping_address_line2",
            "shipping_city",
            "shipping_state",
            "shipping_postal_code",
            "shipping_country",
            "tracking_number",
            "tracking_url",
            "shipped_at",
            "delivered_at",
            "customer_notes",
            "items",
            "can_cancel",
            "created_at",
            "updated_at",
        ]


class OrderCreateSerializer(serializers.Serializer):
    """
    Serializer for creating an order from the current cart.

    Validates stock availability, captures price snapshots, and
    decrements inventory atomically.
    """

    shipping_full_name = serializers.CharField(max_length=255)
    shipping_phone = serializers.CharField(max_length=20, required=False, default="")
    shipping_address_line1 = serializers.CharField(max_length=255)
    shipping_address_line2 = serializers.CharField(
        max_length=255, required=False, default=""
    )
    shipping_city = serializers.CharField(max_length=100)
    shipping_state = serializers.CharField(max_length=100)
    shipping_postal_code = serializers.CharField(max_length=20)
    shipping_country = serializers.CharField(max_length=100, default="US")
    customer_notes = serializers.CharField(required=False, default="")

    @transaction.atomic
    def create(self, validated_data):
        request = self.context["request"]
        user = request.user

        # Get the user's cart
        from apps.cart.models import Cart

        try:
            cart = Cart.objects.prefetch_related(
                "items__product__vendor", "items__product__images"
            ).get(user=user)
        except Cart.DoesNotExist:
            raise serializers.ValidationError("Your cart is empty.")

        cart_items = cart.items.all()
        if not cart_items.exists():
            raise serializers.ValidationError("Your cart is empty.")

        # Validate stock for all items
        stock_errors = []
        for cart_item in cart_items:
            product = cart_item.product
            if product.track_inventory and product.stock_quantity < cart_item.quantity:
                stock_errors.append(
                    f"'{product.name}' only has {product.stock_quantity} units available "
                    f"(you requested {cart_item.quantity})."
                )
            if product.status != "active":
                stock_errors.append(
                    f"'{product.name}' is no longer available."
                )

        if stock_errors:
            raise serializers.ValidationError({"stock_errors": stock_errors})

        # Calculate totals
        subtotal = sum(
            item.product.price * item.quantity for item in cart_items
        )
        shipping_cost = self._calculate_shipping(cart_items)
        tax_amount = self._calculate_tax(subtotal, validated_data.get("shipping_state", ""))
        total_amount = subtotal + shipping_cost + tax_amount

        # Create the order
        order = Order.objects.create(
            customer=user,
            subtotal=subtotal,
            shipping_cost=shipping_cost,
            tax_amount=tax_amount,
            total_amount=total_amount,
            **validated_data,
        )

        # Create order items and decrement stock
        for cart_item in cart_items:
            product = cart_item.product

            OrderItem.objects.create(
                order=order,
                product=product,
                vendor=product.vendor,
                product_name=product.name,
                product_sku=product.sku,
                unit_price=product.price,
                quantity=cart_item.quantity,
            )

            # Atomically decrement stock
            if not product.decrement_stock(cart_item.quantity):
                raise serializers.ValidationError(
                    f"Failed to reserve stock for '{product.name}'. Please try again."
                )

        # Clear the cart
        cart.items.all().delete()

        # Update customer metrics
        if hasattr(user, "customer_profile"):
            profile = user.customer_profile
            profile.total_orders += 1
            profile.total_spent += total_amount
            profile.save(update_fields=["total_orders", "total_spent", "updated_at"])

        return order

    def _calculate_shipping(self, cart_items):
        """Calculate shipping cost based on cart contents."""
        # Simple flat rate + per-item calculation
        from decimal import Decimal

        base_rate = Decimal("5.99")
        per_item_rate = Decimal("1.50")
        total_items = sum(item.quantity for item in cart_items)

        # Free shipping for orders with 5+ items
        if total_items >= 5:
            return Decimal("0.00")

        return base_rate + (per_item_rate * (total_items - 1))

    def _calculate_tax(self, subtotal, state):
        """Calculate sales tax based on state."""
        from decimal import Decimal

        # Simplified US state tax rates
        tax_rates = {
            "CA": Decimal("0.0725"),
            "NY": Decimal("0.08"),
            "TX": Decimal("0.0625"),
            "FL": Decimal("0.06"),
            "WA": Decimal("0.065"),
            "IL": Decimal("0.0625"),
        }
        rate = tax_rates.get(state.upper(), Decimal("0.05"))
        return (subtotal * rate).quantize(Decimal("0.01"))


class VendorOrderSerializer(serializers.ModelSerializer):
    """Serializer for vendor's view of orders (only their items)."""

    items = serializers.SerializerMethodField()
    customer_name = serializers.CharField(source="customer.full_name", read_only=True)
    customer_email = serializers.CharField(source="customer.email", read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "order_number",
            "customer_name",
            "customer_email",
            "status",
            "payment_status",
            "total_amount",
            "shipping_full_name",
            "shipping_city",
            "shipping_state",
            "shipping_country",
            "tracking_number",
            "items",
            "created_at",
        ]

    def get_items(self, obj):
        """Return only the items belonging to the requesting vendor."""
        request = self.context.get("request")
        if request and request.user.is_vendor:
            vendor_items = obj.items.filter(vendor=request.user.vendor_profile)
            return OrderItemSerializer(
                vendor_items, many=True, context=self.context
            ).data
        return []
