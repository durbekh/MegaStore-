"""
Coupon and discount models for MegaStore.

Supports percentage and fixed-amount coupons, vendor-specific coupons,
usage limits, and minimum order requirements.
"""

import uuid

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class Coupon(models.Model):
    """
    Discount coupon that can be applied to orders.

    Supports both platform-wide coupons (created by admins) and
    vendor-specific coupons (created by vendors for their own products).
    Tracks usage counts and enforces expiration dates and limits.
    """

    class DiscountType(models.TextChoices):
        PERCENTAGE = "percentage", "Percentage"
        FIXED_AMOUNT = "fixed_amount", "Fixed Amount"
        FREE_SHIPPING = "free_shipping", "Free Shipping"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text="Unique coupon code customers enter at checkout.",
    )
    description = models.TextField(
        blank=True,
        help_text="Internal description for this coupon.",
    )

    # Discount configuration
    discount_type = models.CharField(
        max_length=20,
        choices=DiscountType.choices,
        default=DiscountType.PERCENTAGE,
    )
    discount_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
        help_text="Percentage (1-100) or fixed amount in USD.",
    )
    max_discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0.01)],
        help_text="Maximum discount amount (for percentage coupons).",
    )

    # Restrictions
    minimum_order_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Minimum order subtotal required to use this coupon.",
    )
    vendor = models.ForeignKey(
        "accounts.VendorProfile",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="coupons",
        help_text="If set, coupon only applies to this vendor's products.",
    )
    applicable_categories = models.ManyToManyField(
        "products.Category",
        blank=True,
        related_name="coupons",
        help_text="If set, coupon only applies to products in these categories.",
    )

    # Usage limits
    usage_limit = models.PositiveIntegerField(
        default=0,
        help_text="Maximum total uses across all customers (0 = unlimited).",
    )
    usage_limit_per_user = models.PositiveIntegerField(
        default=1,
        help_text="Maximum uses per individual customer.",
    )
    times_used = models.PositiveIntegerField(default=0)

    # Validity
    is_active = models.BooleanField(default=True)
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_coupons",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "coupon"
        verbose_name_plural = "coupons"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["code"]),
            models.Index(fields=["valid_from", "valid_until"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        if self.discount_type == self.DiscountType.PERCENTAGE:
            return f"{self.code} ({self.discount_value}% off)"
        elif self.discount_type == self.DiscountType.FIXED_AMOUNT:
            return f"{self.code} (${self.discount_value} off)"
        return f"{self.code} (Free Shipping)"

    @property
    def is_valid(self):
        """Check if the coupon is currently valid."""
        now = timezone.now()
        if not self.is_active:
            return False
        if now < self.valid_from or now > self.valid_until:
            return False
        if self.usage_limit > 0 and self.times_used >= self.usage_limit:
            return False
        return True

    @property
    def is_expired(self):
        return timezone.now() > self.valid_until

    def can_use(self, user, order_subtotal):
        """
        Check if a specific user can use this coupon on an order.

        Returns (bool, str) tuple: (can_use, reason_if_not).
        """
        if not self.is_valid:
            if self.is_expired:
                return False, "This coupon has expired."
            return False, "This coupon is not currently active."

        if order_subtotal < self.minimum_order_amount:
            return False, (
                f"Minimum order amount of ${self.minimum_order_amount:.2f} "
                f"required to use this coupon."
            )

        # Check per-user usage limit
        user_usage = CouponUsage.objects.filter(
            coupon=self,
            user=user,
        ).count()
        if user_usage >= self.usage_limit_per_user:
            return False, "You have already used this coupon the maximum number of times."

        return True, ""

    def calculate_discount(self, subtotal):
        """
        Calculate the discount amount for a given subtotal.

        Returns the discount amount as a Decimal.
        """
        from decimal import Decimal

        if self.discount_type == self.DiscountType.PERCENTAGE:
            discount = subtotal * (self.discount_value / Decimal("100"))
            if self.max_discount_amount:
                discount = min(discount, self.max_discount_amount)
            return discount.quantize(Decimal("0.01"))

        elif self.discount_type == self.DiscountType.FIXED_AMOUNT:
            return min(self.discount_value, subtotal)

        # Free shipping returns 0 as the discount (shipping handled separately)
        return Decimal("0.00")

    def record_usage(self, user, order):
        """Record that this coupon was used by a user on an order."""
        CouponUsage.objects.create(
            coupon=self,
            user=user,
            order=order,
        )
        self.times_used += 1
        self.save(update_fields=["times_used", "updated_at"])


class CouponUsage(models.Model):
    """
    Tracks individual uses of a coupon.

    Links a coupon to the user and order where it was applied,
    along with the actual discount amount granted.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    coupon = models.ForeignKey(
        Coupon,
        on_delete=models.CASCADE,
        related_name="usages",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="coupon_usages",
    )
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.CASCADE,
        related_name="coupon_usages",
    )
    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
    )
    used_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "coupon usage"
        verbose_name_plural = "coupon usages"
        ordering = ["-used_at"]

    def __str__(self):
        return f"{self.coupon.code} used by {self.user.email} on {self.order.order_number}"
