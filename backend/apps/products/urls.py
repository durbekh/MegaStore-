"""URL patterns for the products application."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"", views.ProductViewSet, basename="product")

app_name = "products"

urlpatterns = [
    # Category endpoints
    path("categories/", views.CategoryListView.as_view(), name="category-list"),
    path(
        "categories/<slug:slug>/",
        views.CategoryDetailView.as_view(),
        name="category-detail",
    ),
    # Search
    path("search/", views.ProductSearchView.as_view(), name="product-search"),
    # Product image deletion
    path(
        "images/<uuid:pk>/",
        views.ProductImageDeleteView.as_view(),
        name="product-image-delete",
    ),
    # Product ViewSet routes (must be last to avoid slug conflicts)
    path("", include(router.urls)),
]
