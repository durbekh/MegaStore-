"""URL patterns for the cart application."""

from django.urls import path

from . import views

app_name = "cart"

urlpatterns = [
    path("", views.CartView.as_view(), name="cart-detail"),
    path("items/", views.AddToCartView.as_view(), name="cart-add"),
    path(
        "items/<uuid:item_id>/",
        views.UpdateCartItemView.as_view(),
        name="cart-update-item",
    ),
    path(
        "items/<uuid:item_id>/remove/",
        views.RemoveCartItemView.as_view(),
        name="cart-remove-item",
    ),
    path("clear/", views.ClearCartView.as_view(), name="cart-clear"),
    path("summary/", views.CartSummaryView.as_view(), name="cart-summary"),
]
