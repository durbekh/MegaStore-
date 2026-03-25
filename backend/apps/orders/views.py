"""
Views for the orders application.

Handles order creation, listing, detail views, cancellation,
and vendor-side order management and fulfillment.
"""

import logging

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsCustomer, IsVendor

from .models import Order, OrderItem
from .serializers import (
    OrderCreateSerializer,
    OrderDetailSerializer,
    OrderListSerializer,
    VendorOrderSerializer,
)
from .tasks import send_order_confirmation_email, send_order_status_update_email

logger = logging.getLogger(__name__)


class OrderListView(generics.ListAPIView):
    """
    List orders for the authenticated customer.

    Returns a paginated list of the customer's orders,
    sorted by most recent first.
    """

    serializer_class = OrderListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(
            customer=self.request.user
        ).prefetch_related("items__product__images").order_by("-created_at")


class OrderDetailView(generics.RetrieveAPIView):
    """
    Retrieve detailed information about a specific order.

    Customers can only view their own orders. Admins can view any order.
    """

    serializer_class = OrderDetailSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_admin or user.is_superuser:
            return Order.objects.all()
        return Order.objects.filter(customer=user)

    def get_object(self):
        queryset = self.get_queryset()
        order = generics.get_object_or_404(
            queryset.prefetch_related(
                "items__product__images",
                "items__vendor",
            ),
            pk=self.kwargs["pk"],
        )
        return order


class OrderCreateView(generics.CreateAPIView):
    """
    Create a new order from the current cart.

    Validates stock, captures price snapshots, decrements inventory,
    clears the cart, and triggers order confirmation email.
    """

    serializer_class = OrderCreateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = serializer.save()

        # Send confirmation email asynchronously
        send_order_confirmation_email.delay(str(order.id))

        logger.info(
            "Order %s created by customer %s (total: $%s)",
            order.order_number,
            request.user.email,
            order.total_amount,
        )

        return Response(
            OrderDetailSerializer(order, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class OrderCancelView(APIView):
    """
    Cancel an order.

    Only the customer who placed the order can cancel it,
    and only if it has not been shipped yet.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            order = Order.objects.get(pk=pk, customer=request.user)
        except Order.DoesNotExist:
            return Response(
                {"error": "Order not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not order.can_cancel:
            return Response(
                {"error": "This order cannot be cancelled in its current status."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            order.cancel()
        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Send cancellation email
        send_order_status_update_email.delay(str(order.id), "cancelled")

        logger.info("Order %s cancelled by customer %s", order.order_number, request.user.email)

        return Response(
            {"message": f"Order {order.order_number} has been cancelled."},
            status=status.HTTP_200_OK,
        )


class VendorOrderListView(generics.ListAPIView):
    """
    List orders containing items from the authenticated vendor.

    Returns orders that have at least one item from the vendor's store.
    """

    serializer_class = VendorOrderSerializer
    permission_classes = [permissions.IsAuthenticated, IsVendor]

    def get_queryset(self):
        vendor = self.request.user.vendor_profile
        return (
            Order.objects.filter(items__vendor=vendor)
            .distinct()
            .prefetch_related("items__product__images", "items__vendor")
            .order_by("-created_at")
        )


class VendorOrderFulfillView(APIView):
    """
    Mark a vendor's items in an order as fulfilled.

    Vendors can only fulfill their own items. When all items
    in an order are fulfilled, the order status is updated accordingly.
    """

    permission_classes = [permissions.IsAuthenticated, IsVendor]

    def post(self, request, pk):
        vendor = request.user.vendor_profile

        try:
            order = Order.objects.get(pk=pk)
        except Order.DoesNotExist:
            return Response(
                {"error": "Order not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Get the vendor's items in this order
        vendor_items = order.items.filter(vendor=vendor, is_fulfilled=False)

        if not vendor_items.exists():
            return Response(
                {"error": "No unfulfilled items found for your store in this order."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Fulfill all vendor items
        for item in vendor_items:
            item.fulfill()

        # Optional tracking info
        tracking_number = request.data.get("tracking_number", "")
        tracking_url = request.data.get("tracking_url", "")

        # Check if all items in the order are now fulfilled
        all_fulfilled = not order.items.filter(is_fulfilled=False).exists()

        if all_fulfilled:
            order.mark_shipped(tracking_number, tracking_url)
            send_order_status_update_email.delay(str(order.id), "shipped")
            message = f"All items fulfilled. Order {order.order_number} marked as shipped."
        else:
            message = (
                f"Your items in order {order.order_number} have been marked as fulfilled. "
                f"Waiting for other vendors to fulfill their items."
            )

        logger.info(
            "Vendor %s fulfilled items in order %s",
            vendor.store_name,
            order.order_number,
        )

        return Response({"message": message}, status=status.HTTP_200_OK)


class VendorSalesStatsView(APIView):
    """
    Sales statistics for the authenticated vendor.

    Returns summary metrics: total orders, revenue, average order value.
    """

    permission_classes = [permissions.IsAuthenticated, IsVendor]

    def get(self, request):
        from django.db.models import Avg, Count, Sum

        vendor = request.user.vendor_profile

        # Calculate vendor-specific stats from order items
        stats = OrderItem.objects.filter(
            vendor=vendor,
            order__payment_status="paid",
        ).aggregate(
            total_revenue=Sum("unit_price") or 0,
            total_orders=Count("order", distinct=True),
            total_items_sold=Sum("quantity") or 0,
        )

        # Recent orders
        recent_orders = (
            Order.objects.filter(items__vendor=vendor)
            .distinct()
            .order_by("-created_at")[:5]
        )

        return Response(
            {
                "total_revenue": str(stats["total_revenue"] or 0),
                "total_orders": stats["total_orders"] or 0,
                "total_items_sold": stats["total_items_sold"] or 0,
                "recent_orders": VendorOrderSerializer(
                    recent_orders,
                    many=True,
                    context={"request": request},
                ).data,
            }
        )
