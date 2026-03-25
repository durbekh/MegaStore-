"""Admin configuration for the accounts application."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html

from .models import Address, CustomerProfile, User, VendorProfile


class CustomerProfileInline(admin.StackedInline):
    model = CustomerProfile
    can_delete = False
    verbose_name = "Customer Profile"
    verbose_name_plural = "Customer Profile"
    readonly_fields = ("loyalty_points", "total_orders", "total_spent")


class VendorProfileInline(admin.StackedInline):
    model = VendorProfile
    can_delete = False
    verbose_name = "Vendor Profile"
    verbose_name_plural = "Vendor Profile"
    readonly_fields = (
        "total_sales",
        "total_products",
        "average_rating",
        "approved_at",
    )


class AddressInline(admin.TabularInline):
    model = Address
    extra = 0
    readonly_fields = ("created_at",)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom admin interface for the User model."""

    list_display = (
        "email",
        "full_name",
        "role",
        "is_active",
        "is_email_verified",
        "date_joined",
    )
    list_filter = ("role", "is_active", "is_email_verified", "is_staff", "date_joined")
    search_fields = ("email", "first_name", "last_name")
    ordering = ("-date_joined",)

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            "Personal Information",
            {"fields": ("first_name", "last_name", "phone", "avatar")},
        ),
        (
            "Permissions",
            {
                "fields": (
                    "role",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "is_email_verified",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (
            "Important Dates",
            {"fields": ("last_login", "date_joined")},
        ),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "first_name",
                    "last_name",
                    "role",
                    "password1",
                    "password2",
                ),
            },
        ),
    )

    def get_inlines(self, request, obj=None):
        if obj is None:
            return []
        inlines = [AddressInline]
        if obj.role == User.Role.CUSTOMER:
            inlines.insert(0, CustomerProfileInline)
        elif obj.role == User.Role.VENDOR:
            inlines.insert(0, VendorProfileInline)
        return inlines


@admin.register(VendorProfile)
class VendorProfileAdmin(admin.ModelAdmin):
    """Admin interface for vendor profiles."""

    list_display = (
        "store_name",
        "user_email",
        "status",
        "total_products",
        "total_sales",
        "average_rating",
        "created_at",
    )
    list_filter = ("status", "country", "created_at")
    search_fields = ("store_name", "user__email", "user__first_name")
    readonly_fields = (
        "total_sales",
        "total_products",
        "average_rating",
        "approved_at",
        "created_at",
        "updated_at",
    )
    actions = ["approve_vendors", "suspend_vendors"]

    def user_email(self, obj):
        return obj.user.email

    user_email.short_description = "Email"

    @admin.action(description="Approve selected vendors")
    def approve_vendors(self, request, queryset):
        count = 0
        for vendor in queryset.filter(status=VendorProfile.Status.PENDING):
            vendor.approve()
            count += 1
        self.message_user(request, f"{count} vendor(s) approved.")

    @admin.action(description="Suspend selected vendors")
    def suspend_vendors(self, request, queryset):
        count = queryset.update(status=VendorProfile.Status.SUSPENDED)
        self.message_user(request, f"{count} vendor(s) suspended.")


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    """Admin interface for customer profiles."""

    list_display = (
        "user_email",
        "user_name",
        "loyalty_points",
        "total_orders",
        "total_spent",
        "created_at",
    )
    search_fields = ("user__email", "user__first_name", "user__last_name")
    readonly_fields = (
        "loyalty_points",
        "total_orders",
        "total_spent",
        "created_at",
        "updated_at",
    )

    def user_email(self, obj):
        return obj.user.email

    user_email.short_description = "Email"

    def user_name(self, obj):
        return obj.user.full_name

    user_name.short_description = "Name"


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    """Admin interface for addresses."""

    list_display = (
        "label",
        "user_email",
        "full_name",
        "city",
        "state",
        "country",
        "is_default",
    )
    list_filter = ("address_type", "country", "is_default")
    search_fields = ("user__email", "full_name", "city")

    def user_email(self, obj):
        return obj.user.email

    user_email.short_description = "User"
