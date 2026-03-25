"""URL patterns for the orders application."""

from django.urls import path

from . import views

app_name = "orders"

urlpatterns = [
    # Customer order endpoints
    path("", views.OrderListView.as_view(), name="order-list"),
    path("create/", views.OrderCreateView.as_view(), name="order-create"),
    path("<uuid:pk>/", views.OrderDetailView.as_view(), name="order-detail"),
    path("<uuid:pk>/cancel/", views.OrderCancelView.as_view(), name="order-cancel"),
    # Vendor order endpoints
    path("vendor/", views.VendorOrderListView.as_view(), name="vendor-order-list"),
    path(
        "vendor/<uuid:pk>/fulfill/",
        views.VendorOrderFulfillView.as_view(),
        name="vendor-order-fulfill",
    ),
    path(
        "vendor/stats/",
        views.VendorSalesStatsView.as_view(),
        name="vendor-sales-stats",
    ),
]
