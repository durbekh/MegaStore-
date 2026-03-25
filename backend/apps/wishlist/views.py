"""
Views for the wishlist application.

Handles wishlist management, item addition/removal,
and moving items to cart.
"""

import logging

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cart.models import Cart, CartItem
from apps.products.models import Product

from .models import Wishlist, WishlistItem
from .serializers import (
    AddToWishlistSerializer,
    WishlistListSerializer,
    WishlistSerializer,
)

logger = logging.getLogger(__name__)


class WishlistListView(generics.ListCreateAPIView):
    """
    List all wishlists for the authenticated user, or create a new one.

    GET: Returns all wishlists with item counts.
    POST: Creates a new named wishlist.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return WishlistSerializer
        return WishlistListSerializer

    def get_queryset(self):
        return Wishlist.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class WishlistDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or delete a wishlist.

    The default wishlist cannot be deleted.
    """

    serializer_class = WishlistSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Wishlist.objects.filter(
            user=self.request.user
        ).prefetch_related(
            "items__product__vendor",
            "items__product__images",
        )

    def destroy(self, request, *args, **kwargs):
        wishlist = self.get_object()
        if wishlist.is_default:
            return Response(
                {"error": "Cannot delete the default wishlist."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        wishlist.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AddToWishlistView(APIView):
    """
    Add a product to a wishlist.

    If no wishlist_id is provided, adds to the default wishlist.
    Records the product price at the time of addition for
    price-drop tracking.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = AddToWishlistSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        product_id = serializer.validated_data["product_id"]
        wishlist_id = serializer.validated_data.get("wishlist_id")
        note = serializer.validated_data.get("note", "")

        product = Product.objects.get(id=product_id)

        if wishlist_id:
            wishlist = Wishlist.objects.get(id=wishlist_id, user=request.user)
        else:
            wishlist = Wishlist.get_default(request.user)

        # Check if product is already in this wishlist
        if WishlistItem.objects.filter(wishlist=wishlist, product=product).exists():
            return Response(
                {"message": "Product is already in this wishlist."},
                status=status.HTTP_200_OK,
            )

        WishlistItem.objects.create(
            wishlist=wishlist,
            product=product,
            price_when_added=product.price,
            note=note,
        )

        logger.info(
            "User %s added '%s' to wishlist '%s'",
            request.user.email,
            product.name,
            wishlist.name,
        )

        return Response(
            {"message": f"'{product.name}' added to {wishlist.name}."},
            status=status.HTTP_201_CREATED,
        )


class RemoveFromWishlistView(APIView):
    """Remove a product from a wishlist."""

    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, item_id):
        try:
            item = WishlistItem.objects.get(
                id=item_id,
                wishlist__user=request.user,
            )
            product_name = item.product.name
            item.delete()

            logger.info(
                "User %s removed '%s' from wishlist",
                request.user.email,
                product_name,
            )

            return Response(status=status.HTTP_204_NO_CONTENT)
        except WishlistItem.DoesNotExist:
            return Response(
                {"error": "Wishlist item not found."},
                status=status.HTTP_404_NOT_FOUND,
            )


class MoveToCartView(APIView):
    """
    Move a wishlist item to the shopping cart.

    Adds the product to the cart and removes it from the wishlist.
    Validates stock availability before moving.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, item_id):
        try:
            wishlist_item = WishlistItem.objects.select_related(
                "product"
            ).get(
                id=item_id,
                wishlist__user=request.user,
            )
        except WishlistItem.DoesNotExist:
            return Response(
                {"error": "Wishlist item not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        product = wishlist_item.product

        # Check availability
        if not product.is_in_stock:
            return Response(
                {"error": f"'{product.name}' is currently out of stock."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if product.status != Product.Status.ACTIVE:
            return Response(
                {"error": f"'{product.name}' is no longer available."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Add to cart
        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={"quantity": 1},
        )

        if not created:
            cart_item.quantity += 1
            cart_item.save()

        # Remove from wishlist
        wishlist_item.delete()

        logger.info(
            "User %s moved '%s' from wishlist to cart",
            request.user.email,
            product.name,
        )

        return Response(
            {"message": f"'{product.name}' moved to your cart."},
            status=status.HTTP_200_OK,
        )
