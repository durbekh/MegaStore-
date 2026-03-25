"""Admin configuration for the orders application."""

from django.contrib import admin

from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = (
        "product",
        "vendor",
        "product_name",
        "product_sku",
        "unit_price",
        "quantity",
        "total_price",
        "is_fulfilled",
        "fulfilled_at",
    )
    can_delete = False

    def total_price(self, obj):
        return obj.total_price

    total_price.short_description = "Total"


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "order_number",
        "customer_email",
        "status",
        "payment_status",
        "total_amount",
        "item_count",
        "created_at",
    )
    list_filter = ("status", "payment_status", "created_at")
    search_fields = ("order_number", "customer__email", "customer__first_name")
    readonly_fields = (
        "order_number",
        "customer",
        "subtotal",
        "shipping_cost",
        "tax_amount",
        "discount_amount",
        "total_amount",
        "platform_fee",
        "stripe_payment_intent_id",
        "paid_at",
        "shipped_at",
        "delivered_at",
        "created_at",
        "updated_at",
    )
    inlines = [OrderItemInline]
    list_per_page = 25
    date_hierarchy = "created_at"

    fieldsets = (
        (
            "Order Info",
            {
                "fields": (
                    "order_number",
                    "customer",
                    "status",
                )
            },
        ),
        (
            "Financial",
            {
                "fields": (
                    "subtotal",
                    "shipping_cost",
                    "tax_amount",
                    "discount_amount",
                    "total_amount",
                    "platform_fee",
                )
            },
        ),
        (
            "Payment",
            {
                "fields": (
                    "payment_status",
                    "stripe_payment_intent_id",
                    "paid_at",
                )
            },
        ),
        (
            "Shipping",
            {
                "fields": (
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
                )
            },
        ),
        (
            "Notes",
            {
                "fields": ("customer_notes", "internal_notes"),
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

    def customer_email(self, obj):
        return obj.customer.email

    customer_email.short_description = "Customer"

    def item_count(self, obj):
        return obj.items.count()

    item_count.short_description = "Items"

    actions = ["mark_processing", "mark_shipped", "mark_delivered"]

    @admin.action(description="Mark as Processing")
    def mark_processing(self, request, queryset):
        queryset.filter(status=Order.Status.CONFIRMED).update(
            status=Order.Status.PROCESSING
        )

    @admin.action(description="Mark as Shipped")
    def mark_shipped(self, request, queryset):
        for order in queryset.filter(status__in=[Order.Status.CONFIRMED, Order.Status.PROCESSING]):
            order.mark_shipped()

    @admin.action(description="Mark as Delivered")
    def mark_delivered(self, request, queryset):
        for order in queryset.filter(status=Order.Status.SHIPPED):
            order.mark_delivered()
