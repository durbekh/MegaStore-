"""
Serializers for the coupons application.

Handles coupon validation, application, and management.
"""

from django.utils import timezone
from rest_framework import serializers

from .models import Coupon, CouponUsage


class CouponSerializer(serializers.ModelSerializer):
    """Serializer for coupon display (vendor/admin view)."""

    is_valid = serializers.ReadOnlyField()
    is_expired = serializers.ReadOnlyField()
    vendor_name = serializers.CharField(
        source="vendor.store_name", read_only=True, default=None
    )

    class Meta:
        model = Coupon
        fields = [
            "id",
            "code",
            "description",
            "discount_type",
            "discount_value",
            "max_discount_amount",
            "minimum_order_amount",
            "vendor_name",
            "usage_limit",
            "usage_limit_per_user",
            "times_used",
            "is_active",
            "is_valid",
            "is_expired",
            "valid_from",
            "valid_until",
            "created_at",
        ]
        read_only_fields = ["id", "times_used", "created_at"]


class CouponCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating coupons (vendor or admin)."""

    class Meta:
        model = Coupon
        fields = [
            "code",
            "description",
            "discount_type",
            "discount_value",
            "max_discount_amount",
            "minimum_order_amount",
            "usage_limit",
            "usage_limit_per_user",
            "valid_from",
            "valid_until",
        ]

    def validate_code(self, value):
        """Ensure coupon code is unique and uppercase."""
        code = value.upper().strip()
        if Coupon.objects.filter(code=code).exists():
            raise serializers.ValidationError("A coupon with this code already exists.")
        return code

    def validate(self, attrs):
        """Validate discount value and date range."""
        discount_type = attrs.get("discount_type")
        discount_value = attrs.get("discount_value")
        valid_from = attrs.get("valid_from")
        valid_until = attrs.get("valid_until")

        if discount_type == Coupon.DiscountType.PERCENTAGE and discount_value > 100:
            raise serializers.ValidationError(
                {"discount_value": "Percentage discount cannot exceed 100%."}
            )

        if valid_from and valid_until and valid_from >= valid_until:
            raise serializers.ValidationError(
                {"valid_until": "End date must be after start date."}
            )

        if valid_until and valid_until < timezone.now():
            raise serializers.ValidationError(
                {"valid_until": "End date cannot be in the past."}
            )

        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        validated_data["created_by"] = request.user

        # If the user is a vendor, tie the coupon to their store
        if request.user.is_vendor:
            validated_data["vendor"] = request.user.vendor_profile

        return Coupon.objects.create(**validated_data)


class ApplyCouponSerializer(serializers.Serializer):
    """Serializer for applying a coupon to the current cart/order."""

    code = serializers.CharField(max_length=50)

    def validate_code(self, value):
        code = value.upper().strip()
        try:
            coupon = Coupon.objects.get(code=code)
        except Coupon.DoesNotExist:
            raise serializers.ValidationError("Invalid coupon code.")

        if not coupon.is_valid:
            if coupon.is_expired:
                raise serializers.ValidationError("This coupon has expired.")
            raise serializers.ValidationError("This coupon is not currently active.")

        return code
