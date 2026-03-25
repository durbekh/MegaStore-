"""
Order models for MegaStore.

Defines Order, OrderItem, and related models for managing
the complete order lifecycle in the marketplace.
"""

import uuid
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class Order(models.Model):
    """
    Represents a customer order in the marketplace.

    An order contains one or more OrderItems, each linked to a specific
    product and vendor. The order tracks its lifecycle status, payment
    information, and shipping details.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CONFIRMED = "confirmed", "Confirmed"
        PROCESSING = "processing", "Processing"
        SHIPPED = "shipped", "Shipped"
        DELIVERED = "delivered", "Delivered"
        CANCELLED = "cancelled", "Cancelled"
        REFUNDED = "refunded", "Refunded"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_number = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        editable=False,
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="orders",
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )

    # Financial
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    shipping_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
    )
    tax_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
    )
    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
    )
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    platform_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
    )

    # Payment
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True)
    payment_status = models.CharField(
        max_length=20,
        choices=[
            ("unpaid", "Unpaid"),
            ("paid", "Paid"),
            ("refunded", "Refunded"),
            ("failed", "Failed"),
        ],
        default="unpaid",
        db_index=True,
    )
    paid_at = models.DateTimeField(null=True, blank=True)

    # Shipping Address
    shipping_full_name = models.CharField(max_length=255)
    shipping_phone = models.CharField(max_length=20, blank=True)
    shipping_address_line1 = models.CharField(max_length=255)
    shipping_address_line2 = models.CharField(max_length=255, blank=True)
    shipping_city = models.CharField(max_length=100)
    shipping_state = models.CharField(max_length=100)
    shipping_postal_code = models.CharField(max_length=20)
    shipping_country = models.CharField(max_length=100, default="US")

    # Tracking
    tracking_number = models.CharField(max_length=100, blank=True)
    tracking_url = models.URLField(blank=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    # Notes
    customer_notes = models.TextField(blank=True)
    internal_notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "order"
        verbose_name_plural = "orders"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["order_number"]),
            models.Index(fields=["customer", "status"]),
            models.Index(fields=["-created_at"]),
            models.Index(fields=["payment_status"]),
        ]

    def __str__(self):
        return f"Order {self.order_number}"

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self._generate_order_number()
        if not self.total_amount:
            self.calculate_totals()
        super().save(*args, **kwargs)

    def _generate_order_number(self):
        """Generate a unique order number with prefix and timestamp."""
        now = timezone.now()
        prefix = f"MS{now.strftime('%Y%m%d')}"
        last_order = (
            Order.objects.filter(order_number__startswith=prefix)
            .order_by("-order_number")
            .first()
        )
        if last_order:
            last_seq = int(last_order.order_number[-5:])
            seq = str(last_seq + 1).zfill(5)
        else:
            seq = "00001"
        return f"{prefix}{seq}"

    def calculate_totals(self):
        """Recalculate order totals from items."""
        items = self.items.all()
        self.subtotal = sum(item.total_price for item in items)
        self.total_amount = (
            self.subtotal + self.shipping_cost + self.tax_amount - self.discount_amount
        )
        self.platform_fee = self.subtotal * (
            Decimal(str(settings.PLATFORM_FEE_PERCENT)) / Decimal("100")
        )

    def confirm_payment(self, payment_intent_id):
        """Mark the order as paid and confirmed."""
        self.status = self.Status.CONFIRMED
        self.payment_status = "paid"
        self.stripe_payment_intent_id = payment_intent_id
        self.paid_at = timezone.now()
        self.save(update_fields=[
            "status", "payment_status", "stripe_payment_intent_id",
            "paid_at", "updated_at",
        ])

    def cancel(self):
        """Cancel the order and restore stock."""
        if self.status in [self.Status.SHIPPED, self.Status.DELIVERED]:
            raise ValueError("Cannot cancel a shipped or delivered order.")

        self.status = self.Status.CANCELLED
        self.save(update_fields=["status", "updated_at"])

        # Restore stock for each item
        for item in self.items.all():
            item.product.increment_stock(item.quantity)

    def mark_shipped(self, tracking_number="", tracking_url=""):
        """Mark the order as shipped with optional tracking info."""
        self.status = self.Status.SHIPPED
        self.tracking_number = tracking_number
        self.tracking_url = tracking_url
        self.shipped_at = timezone.now()
        self.save(update_fields=[
            "status", "tracking_number", "tracking_url",
            "shipped_at", "updated_at",
        ])

    def mark_delivered(self):
        """Mark the order as delivered."""
        self.status = self.Status.DELIVERED
        self.delivered_at = timezone.now()
        self.save(update_fields=["status", "delivered_at", "updated_at"])

    @property
    def can_cancel(self):
        return self.status in [self.Status.PENDING, self.Status.CONFIRMED, self.Status.PROCESSING]

    @property
    def vendor_ids(self):
        """Return unique vendor IDs for this order."""
        return list(
            self.items.values_list("product__vendor_id", flat=True).distinct()
        )


class OrderItem(models.Model):
    """
    Individual line item within an order.

    Stores a snapshot of the product price at the time of purchase
    to maintain historical accuracy even if the product price changes.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
    )
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.PROTECT,
        related_name="order_items",
    )
    vendor = models.ForeignKey(
        "accounts.VendorProfile",
        on_delete=models.PROTECT,
        related_name="order_items",
    )

    # Price snapshot at time of purchase
    product_name = models.CharField(max_length=500)
    product_sku = models.CharField(max_length=100)
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    quantity = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
    )

    # Fulfillment status per item (for multi-vendor orders)
    is_fulfilled = models.BooleanField(default=False)
    fulfilled_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "order item"
        verbose_name_plural = "order items"

    def __str__(self):
        return f"{self.quantity}x {self.product_name} in {self.order.order_number}"

    @property
    def total_price(self):
        return self.unit_price * self.quantity

    def fulfill(self):
        """Mark this item as fulfilled by the vendor."""
        self.is_fulfilled = True
        self.fulfilled_at = timezone.now()
        self.save(update_fields=["is_fulfilled", "fulfilled_at"])
