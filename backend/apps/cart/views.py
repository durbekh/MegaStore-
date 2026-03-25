"""
Views for the cart application.

Handles cart retrieval, item addition, quantity updates,
item removal, and cart clearing.
"""

import logging

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.products.models import Product

from .models import Cart, CartItem
from .serializers import (
    AddToCartSerializer,
    CartSerializer,
    UpdateCartItemSerializer,
)

logger = logging.getLogger(__name__)


class CartView(APIView):
    """
    Retrieve the current user's cart.

    GET: Returns the complete cart with all items, quantities,
    prices, and availability status.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        cart, created = Cart.objects.prefetch_related(
            "items__product__vendor",
            "items__product__images",
        ).get_or_create(user=request.user)

        serializer = CartSerializer(cart, context={"request": request})
        return Response(serializer.data)


class AddToCartView(APIView):
    """
    Add a product to the cart.

    If the product is already in the cart, the quantity is incremented.
    Validates stock availability before adding.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = AddToCartSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        product_id = serializer.validated_data["product_id"]
        quantity = serializer.validated_data["quantity"]

        product = Product.objects.get(id=product_id)
        cart, _ = Cart.objects.get_or_create(user=request.user)

        # Check if item already exists in cart
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={"quantity": quantity},
        )

        if not created:
            cart_item.quantity += quantity
            cart_item.save()

        logger.info(
            "User %s added %dx '%s' to cart",
            request.user.email,
            quantity,
            product.name,
        )

        # Return updated cart
        cart.refresh_from_db()
        cart_serializer = CartSerializer(
            cart,
            context={"request": request},
        )
        return Response(cart_serializer.data, status=status.HTTP_200_OK)


class UpdateCartItemView(APIView):
    """
    Update the quantity of a cart item.

    PATCH: Updates the quantity of an existing cart item.
    Validates against available stock.
    """

    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, item_id):
        try:
            cart_item = CartItem.objects.select_related("product").get(
                id=item_id,
                cart__user=request.user,
            )
        except CartItem.DoesNotExist:
            return Response(
                {"error": "Cart item not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = UpdateCartItemSerializer(
            data=request.data,
            context={"cart_item": cart_item},
        )
        serializer.is_valid(raise_exception=True)

        cart_item.quantity = serializer.validated_data["quantity"]
        cart_item.save()

        # Return updated cart
        cart = cart_item.cart
        cart_serializer = CartSerializer(
            cart,
            context={"request": request},
        )
        return Response(cart_serializer.data)


class RemoveCartItemView(APIView):
    """Remove a specific item from the cart."""

    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, item_id):
        try:
            cart_item = CartItem.objects.get(
                id=item_id,
                cart__user=request.user,
            )
        except CartItem.DoesNotExist:
            return Response(
                {"error": "Cart item not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        product_name = cart_item.product.name
        cart = cart_item.cart
        cart_item.delete()

        logger.info(
            "User %s removed '%s' from cart",
            request.user.email,
            product_name,
        )

        cart_serializer = CartSerializer(
            cart,
            context={"request": request},
        )
        return Response(cart_serializer.data)


class ClearCartView(APIView):
    """Remove all items from the cart."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            cart = Cart.objects.get(user=request.user)
            cart.clear()
            logger.info("User %s cleared cart", request.user.email)
        except Cart.DoesNotExist:
            pass

        return Response(
            {"message": "Cart cleared."},
            status=status.HTTP_200_OK,
        )


class CartSummaryView(APIView):
    """
    Get a lightweight cart summary (for header badge).

    Returns only item count and subtotal without full product details.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            cart = Cart.objects.prefetch_related("items__product").get(
                user=request.user
            )
            return Response(
                {
                    "total_items": cart.total_items,
                    "total_unique_items": cart.total_unique_items,
                    "subtotal": str(cart.subtotal),
                }
            )
        except Cart.DoesNotExist:
            return Response(
                {
                    "total_items": 0,
                    "total_unique_items": 0,
                    "subtotal": "0.00",
                }
            )
