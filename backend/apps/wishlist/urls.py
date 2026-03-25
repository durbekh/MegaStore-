"""URL patterns for the wishlist application."""

from django.urls import path

from . import views

app_name = "wishlist"

urlpatterns = [
    path("", views.WishlistListView.as_view(), name="wishlist-list"),
    path("<uuid:pk>/", views.WishlistDetailView.as_view(), name="wishlist-detail"),
    path("items/add/", views.AddToWishlistView.as_view(), name="wishlist-add"),
    path(
        "items/<uuid:item_id>/remove/",
        views.RemoveFromWishlistView.as_view(),
        name="wishlist-remove",
    ),
    path(
        "items/<uuid:item_id>/move-to-cart/",
        views.MoveToCartView.as_view(),
        name="wishlist-move-to-cart",
    ),
]
