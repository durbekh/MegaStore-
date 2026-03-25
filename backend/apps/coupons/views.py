"""
Views for the coupons application.

Handles coupon validation, application, creation, and management.
"""

import logging

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsApprovedVendor, IsVendorOrAdmin
from apps.cart.models import Cart

from .models import Coupon
from .serializers import ApplyCouponSerializer, CouponCreateSerializer, CouponSerializer

logger = logging.getLogger(__name__)


class CouponListView(generics.ListAPIView):
    """
    List coupons for the authenticated vendor or admin.

    Vendors see only their own coupons. Admins see all coupons.
    """

    serializer_class = CouponSerializer
    permission_classes = [permissions.IsAuthenticated, IsVendorOrAdmin]

    def get_queryset(self):
        user = self.request.user
        if user.is_admin or user.is_superuser:
            return Coupon.objects.all()
        return Coupon.objects.filter(vendor=user.vendor_profile)


class CouponCreateView(generics.CreateAPIView):
    """
    Create a new coupon.

    Vendors create coupons for their own products.
    Admins can create platform-wide coupons.
    """

    serializer_class = CouponCreateSerializer
    permission_classes = [permissions.IsAuthenticated, IsVendorOrAdmin]


class CouponDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a coupon (owner or admin only)."""

    serializer_class = CouponSerializer
    permission_classes = [permissions.IsAuthenticated, IsVendorOrAdmin]

    def get_queryset(self):
        user = self.request.user
        if user.is_admin or user.is_superuser:
            return Coupon.objects.all()
        return Coupon.objects.filter(vendor=user.vendor_profile)


class ValidateCouponView(APIView):
    """
    Validate a coupon code against the current user's cart.

    Returns the discount amount that would be applied if the
    coupon is valid for the current cart contents.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ApplyCouponSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        code = serializer.validated_data["code"]
        coupon = Coupon.objects.get(code=code)

        # Get the user's cart subtotal
        try:
            cart = Cart.objects.prefetch_related("items__product").get(
                user=request.user
            )
            subtotal = cart.subtotal
        except Cart.DoesNotExist:
            return Response(
                {"error": "Your cart is empty."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check if the coupon can be used by this user on this order
        can_use, reason = coupon.can_use(request.user, subtotal)
        if not can_use:
            return Response(
                {"error": reason},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check vendor restriction
        if coupon.vendor:
            vendor_items_subtotal = sum(
                item.line_total
                for item in cart.items.select_related("product__vendor").all()
                if item.product.vendor_id == coupon.vendor_id
            )
            if vendor_items_subtotal == 0:
                return Response(
                    {"error": f"This coupon is only valid for products from {coupon.vendor.store_name}."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            discount = coupon.calculate_discount(vendor_items_subtotal)
        else:
            discount = coupon.calculate_discount(subtotal)

        logger.info(
            "Coupon %s validated for user %s (discount: $%s)",
            code,
            request.user.email,
            discount,
        )

        return Response(
            {
                "code": coupon.code,
                "discount_type": coupon.discount_type,
                "discount_value": str(coupon.discount_value),
                "calculated_discount": str(discount),
                "message": f"Coupon applied! You save ${discount:.2f}.",
                "free_shipping": coupon.discount_type == Coupon.DiscountType.FREE_SHIPPING,
            }
        )
