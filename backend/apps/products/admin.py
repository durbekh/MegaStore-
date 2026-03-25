"""Admin configuration for the products application."""

from django.contrib import admin
from django.utils.html import format_html

from .models import Category, Product, ProductImage, Review


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    readonly_fields = ("image_preview",)

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="80" height="80" style="object-fit: cover;" />',
                obj.image.url,
            )
        return "-"

    image_preview.short_description = "Preview"


class ReviewInline(admin.TabularInline):
    model = Review
    extra = 0
    readonly_fields = ("user", "rating", "title", "created_at")
    can_delete = True


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "parent", "is_active", "sort_order", "product_count")
    list_filter = ("is_active", "parent")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("sort_order", "name")

    def product_count(self, obj):
        return obj.products.count()

    product_count.short_description = "Products"


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "vendor_name",
        "category",
        "price",
        "stock_quantity",
        "status",
        "average_rating",
        "total_sold",
        "created_at",
    )
    list_filter = ("status", "is_featured", "category", "created_at")
    search_fields = ("name", "sku", "vendor__store_name")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = (
        "average_rating",
        "review_count",
        "total_sold",
        "view_count",
        "created_at",
        "updated_at",
    )
    inlines = [ProductImageInline, ReviewInline]
    list_per_page = 25

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "vendor",
                    "category",
                    "name",
                    "slug",
                    "description",
                    "short_description",
                )
            },
        ),
        (
            "Pricing",
            {"fields": ("price", "compare_at_price")},
        ),
        (
            "Inventory",
            {
                "fields": (
                    "sku",
                    "stock_quantity",
                    "low_stock_threshold",
                    "track_inventory",
                )
            },
        ),
        (
            "Details",
            {"fields": ("weight", "tags", "brand")},
        ),
        (
            "Status",
            {"fields": ("status", "is_featured")},
        ),
        (
            "Metrics",
            {
                "fields": (
                    "average_rating",
                    "review_count",
                    "total_sold",
                    "view_count",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    def vendor_name(self, obj):
        return obj.vendor.store_name

    vendor_name.short_description = "Vendor"

    actions = ["make_active", "make_inactive", "mark_featured"]

    @admin.action(description="Set status to Active")
    def make_active(self, request, queryset):
        queryset.update(status=Product.Status.ACTIVE)

    @admin.action(description="Set status to Inactive")
    def make_inactive(self, request, queryset):
        queryset.update(status=Product.Status.INACTIVE)

    @admin.action(description="Mark as Featured")
    def mark_featured(self, request, queryset):
        queryset.update(is_featured=True)


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = (
        "product",
        "user",
        "rating",
        "is_verified_purchase",
        "is_approved",
        "created_at",
    )
    list_filter = ("rating", "is_verified_purchase", "is_approved", "created_at")
    search_fields = ("product__name", "user__email", "title")
    readonly_fields = ("created_at", "updated_at")
    actions = ["approve_reviews", "reject_reviews"]

    @admin.action(description="Approve selected reviews")
    def approve_reviews(self, request, queryset):
        queryset.update(is_approved=True)

    @admin.action(description="Reject selected reviews")
    def reject_reviews(self, request, queryset):
        queryset.update(is_approved=False)
