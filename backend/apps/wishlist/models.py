"""
Wishlist models for MegaStore.

Allows customers to save products they are interested in for later
purchase. Supports multiple wishlists per user.
"""

import uuid

from django.conf import settings
from django.db import models


class Wishlist(models.Model):
    """
    A named wishlist belonging to a user.

    Each user has a default wishlist created automatically, and can
    create additional named wishlists for organization.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="wishlists",
    )
    name = models.CharField(
        max_length=100,
        default="My Wishlist",
    )
    is_default = models.BooleanField(default=False)
    is_public = models.BooleanField(
        default=False,
        help_text="Public wishlists can be shared via link.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "wishlist"
        verbose_name_plural = "wishlists"
        ordering = ["-is_default", "-updated_at"]

    def __str__(self):
        return f"{self.name} ({self.user.email})"

    def save(self, *args, **kwargs):
        """Ensure only one default wishlist per user."""
        if self.is_default:
            Wishlist.objects.filter(
                user=self.user,
                is_default=True,
            ).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)

    @property
    def item_count(self):
        return self.items.count()

    @classmethod
    def get_default(cls, user):
        """
        Get or create the user's default wishlist.

        Returns the default wishlist, creating one if it does not exist.
        """
        wishlist, created = cls.objects.get_or_create(
            user=user,
            is_default=True,
            defaults={"name": "My Wishlist"},
        )
        return wishlist


class WishlistItem(models.Model):
    """
    An individual product saved to a wishlist.

    Tracks when the item was added and provides price-drop
    detection by storing the price at the time of addition.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    wishlist = models.ForeignKey(
        Wishlist,
        on_delete=models.CASCADE,
        related_name="items",
    )
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.CASCADE,
        related_name="wishlist_items",
    )
    price_when_added = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Price of the product when it was added to the wishlist.",
    )
    note = models.CharField(
        max_length=500,
        blank=True,
        help_text="Optional personal note about this item.",
    )

    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "wishlist item"
        verbose_name_plural = "wishlist items"
        unique_together = ["wishlist", "product"]
        ordering = ["-added_at"]

    def __str__(self):
        return f"{self.product.name} in {self.wishlist.name}"

    @property
    def has_price_drop(self):
        """Check if the product price has dropped since it was added."""
        return self.product.price < self.price_when_added

    @property
    def price_difference(self):
        """Return the price difference (negative means price dropped)."""
        return self.product.price - self.price_when_added

    @property
    def is_in_stock(self):
        """Check if the product is currently in stock."""
        return self.product.is_in_stock
