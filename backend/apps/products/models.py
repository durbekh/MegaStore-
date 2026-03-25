"""
Product models for MegaStore.

Defines Product, Category, ProductImage, and Review models
for the marketplace catalog system.
"""

import uuid

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.text import slugify


class Category(models.Model):
    """
    Product category with hierarchical structure (parent-child).

    Supports nested categories for organizing the product catalog
    (e.g., Electronics > Phones > Smartphones).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, db_index=True)
    slug = models.SlugField(max_length=200, unique=True, db_index=True)
    description = models.TextField(blank=True)
    image = models.ImageField(
        upload_to="categories/%Y/%m/",
        blank=True,
        null=True,
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
    )
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "category"
        verbose_name_plural = "categories"
        ordering = ["sort_order", "name"]
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["parent"]),
        ]

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    @property
    def full_path(self):
        """Return the full category path (e.g., 'Electronics > Phones > Smartphones')."""
        parts = [self.name]
        parent = self.parent
        while parent:
            parts.insert(0, parent.name)
            parent = parent.parent
        return " > ".join(parts)

    def get_descendants(self):
        """Return all descendant categories (children, grandchildren, etc.)."""
        descendants = list(self.children.all())
        for child in self.children.all():
            descendants.extend(child.get_descendants())
        return descendants


class Product(models.Model):
    """
    Product listing in the marketplace.

    Belongs to a vendor and a category. Tracks inventory, pricing,
    and visibility. Supports Elasticsearch indexing for search.
    """

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"
        OUT_OF_STOCK = "out_of_stock", "Out of Stock"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vendor = models.ForeignKey(
        "accounts.VendorProfile",
        on_delete=models.CASCADE,
        related_name="products",
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
    )
    name = models.CharField(max_length=500, db_index=True)
    slug = models.SlugField(max_length=500, unique=True, db_index=True)
    description = models.TextField()
    short_description = models.CharField(max_length=500, blank=True)

    # Pricing
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
    )
    compare_at_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0.01)],
        help_text="Original price before discount (for display purposes).",
    )

    # Inventory
    sku = models.CharField(
        "SKU",
        max_length=100,
        unique=True,
        db_index=True,
    )
    stock_quantity = models.PositiveIntegerField(default=0)
    low_stock_threshold = models.PositiveIntegerField(
        default=10,
        help_text="Alert vendor when stock drops below this number.",
    )
    track_inventory = models.BooleanField(default=True)

    # Product details
    weight = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Weight in kilograms.",
    )
    tags = models.CharField(
        max_length=500,
        blank=True,
        help_text="Comma-separated tags for search and filtering.",
    )
    brand = models.CharField(max_length=200, blank=True, db_index=True)

    # Status and visibility
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )
    is_featured = models.BooleanField(default=False)

    # Metrics (denormalized for performance)
    average_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
    )
    review_count = models.PositiveIntegerField(default=0)
    total_sold = models.PositiveIntegerField(default=0)
    view_count = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "product"
        verbose_name_plural = "products"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["sku"]),
            models.Index(fields=["status"]),
            models.Index(fields=["-created_at"]),
            models.Index(fields=["price"]),
            models.Index(fields=["-average_rating"]),
            models.Index(fields=["vendor", "status"]),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug

        # Auto-update status based on stock
        if self.track_inventory and self.stock_quantity == 0:
            self.status = self.Status.OUT_OF_STOCK

        super().save(*args, **kwargs)

    @property
    def is_in_stock(self):
        if not self.track_inventory:
            return True
        return self.stock_quantity > 0

    @property
    def is_low_stock(self):
        if not self.track_inventory:
            return False
        return self.stock_quantity <= self.low_stock_threshold

    @property
    def discount_percentage(self):
        """Calculate discount percentage if compare_at_price is set."""
        if self.compare_at_price and self.compare_at_price > self.price:
            discount = ((self.compare_at_price - self.price) / self.compare_at_price) * 100
            return round(discount, 1)
        return 0

    @property
    def primary_image(self):
        """Return the primary image or the first available image."""
        return self.images.filter(is_primary=True).first() or self.images.first()

    def update_rating(self):
        """Recalculate average rating from reviews."""
        from django.db.models import Avg, Count

        stats = self.reviews.aggregate(
            avg_rating=Avg("rating"),
            total_reviews=Count("id"),
        )
        self.average_rating = stats["avg_rating"] or 0
        self.review_count = stats["total_reviews"]
        self.save(update_fields=["average_rating", "review_count", "updated_at"])

    def decrement_stock(self, quantity):
        """
        Atomically decrement stock by the given quantity.

        Uses F() expressions to avoid race conditions.
        Returns True if successful, False if insufficient stock.
        """
        from django.db.models import F

        if not self.track_inventory:
            return True

        updated = Product.objects.filter(
            pk=self.pk,
            stock_quantity__gte=quantity,
        ).update(
            stock_quantity=F("stock_quantity") - quantity,
            total_sold=F("total_sold") + quantity,
        )
        return updated > 0

    def increment_stock(self, quantity):
        """Atomically increment stock (e.g., after order cancellation)."""
        from django.db.models import F

        Product.objects.filter(pk=self.pk).update(
            stock_quantity=F("stock_quantity") + quantity,
        )


class ProductImage(models.Model):
    """
    Product image with ordering support.

    Each product can have multiple images with one marked as primary.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="images",
    )
    image = models.ImageField(upload_to="products/%Y/%m/")
    alt_text = models.CharField(max_length=255, blank=True)
    is_primary = models.BooleanField(default=False)
    sort_order = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "product image"
        verbose_name_plural = "product images"
        ordering = ["sort_order", "-is_primary"]

    def __str__(self):
        return f"Image for {self.product.name} (order: {self.sort_order})"

    def save(self, *args, **kwargs):
        # Ensure only one primary image per product
        if self.is_primary:
            ProductImage.objects.filter(
                product=self.product,
                is_primary=True,
            ).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)


class Review(models.Model):
    """
    Product review by a customer.

    Each customer can only leave one review per product.
    Reviews are linked to verified purchases when possible.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    title = models.CharField(max_length=255)
    comment = models.TextField()
    is_verified_purchase = models.BooleanField(
        default=False,
        help_text="Whether the reviewer has purchased this product.",
    )
    is_approved = models.BooleanField(default=True)

    # Helpfulness voting
    helpful_count = models.PositiveIntegerField(default=0)
    not_helpful_count = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "review"
        verbose_name_plural = "reviews"
        ordering = ["-created_at"]
        unique_together = ["product", "user"]
        indexes = [
            models.Index(fields=["product", "user"]),
            models.Index(fields=["-created_at"]),
            models.Index(fields=["rating"]),
        ]

    def __str__(self):
        return f"Review by {self.user.full_name} for {self.product.name} ({self.rating}/5)"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update the product's average rating
        self.product.update_rating()
