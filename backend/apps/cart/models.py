"""
Cart models for MegaStore.

Provides a persistent server-side shopping cart linked to
authenticated users. Supports quantity management and
stock validation.
"""

import uuid

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class Cart(models.Model):
    """
    Shopping cart for an authenticated user.

    Each user has at most one active cart. The cart persists
    across sessions until it is cleared or converted to an order.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cart",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "cart"
        verbose_name_plural = "carts"

    def __str__(self):
        return f"Cart for {self.user.email}"

    @property
    def total_items(self):
        """Total number of items (sum of quantities) in the cart."""
        return sum(item.quantity for item in self.items.all())

    @property
    def total_unique_items(self):
        """Number of unique products in the cart."""
        return self.items.count()

    @property
    def subtotal(self):
        """Total price of all items in the cart."""
        return sum(item.line_total for item in self.items.select_related("product").all())

    def clear(self):
        """Remove all items from the cart."""
        self.items.all().delete()

    def get_items_by_vendor(self):
        """Group cart items by vendor for display."""
        items = self.items.select_related(
            "product__vendor", "product__vendor__user"
        ).all()

        vendor_groups = {}
        for item in items:
            vendor = item.product.vendor
            if vendor.id not in vendor_groups:
                vendor_groups[vendor.id] = {
                    "vendor_name": vendor.store_name,
                    "vendor_slug": vendor.slug,
                    "items": [],
                    "subtotal": 0,
                }
            vendor_groups[vendor.id]["items"].append(item)
            vendor_groups[vendor.id]["subtotal"] += item.line_total

        return vendor_groups


class CartItem(models.Model):
    """
    Individual item in a shopping cart.

    Linked to a specific product with a quantity. Validates
    against available stock when quantity is updated.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name="items",
    )
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.CASCADE,
        related_name="cart_items",
    )
    quantity = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "cart item"
        verbose_name_plural = "cart items"
        unique_together = ["cart", "product"]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.quantity}x {self.product.name} in cart"

    @property
    def line_total(self):
        """Total price for this line item (price x quantity)."""
        return self.product.price * self.quantity

    @property
    def is_available(self):
        """Check if the product is still available in the requested quantity."""
        if not self.product.track_inventory:
            return True
        return (
            self.product.stock_quantity >= self.quantity
            and self.product.status == "active"
        )

    def save(self, *args, **kwargs):
        """Update the parent cart's updated_at timestamp."""
        super().save(*args, **kwargs)
        Cart.objects.filter(pk=self.cart_id).update(updated_at=models.functions.Now())
