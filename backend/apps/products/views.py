"""
Views for the products application.

Handles product listing, detail, CRUD operations, category browsing,
review management, and search functionality.
"""

import logging

from django.db.models import Avg, Count, Q
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from apps.accounts.permissions import IsApprovedVendor, IsProductOwnerOrAdmin

from .filters import ProductFilter
from .models import Category, Product, ProductImage, Review
from .serializers import (
    CategorySerializer,
    ProductCreateUpdateSerializer,
    ProductDetailSerializer,
    ProductImageSerializer,
    ProductListSerializer,
    ReviewCreateSerializer,
    ReviewSerializer,
)

logger = logging.getLogger(__name__)


class CategoryListView(generics.ListAPIView):
    """
    List all active product categories.

    Returns a hierarchical tree of categories with product counts.
    Cached for 15 minutes.
    """

    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return Category.objects.filter(
            is_active=True,
            parent__isnull=True,
        ).prefetch_related("children")

    @method_decorator(cache_page(60 * 15))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class CategoryDetailView(generics.RetrieveAPIView):
    """Retrieve a single category by slug with its products."""

    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = "slug"
    queryset = Category.objects.filter(is_active=True)


class ProductViewSet(viewsets.ModelViewSet):
    """
    ViewSet for product CRUD operations.

    - List/Retrieve: Public (all active products)
    - Create: Approved vendors only
    - Update/Delete: Product owner or admin only

    Supports filtering by category, price range, rating, vendor,
    and search by name/description.
    """

    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filterset_class = ProductFilter
    search_fields = ["name", "description", "tags", "brand"]
    ordering_fields = ["price", "created_at", "average_rating", "total_sold"]
    ordering = ["-created_at"]
    lookup_field = "slug"

    def get_queryset(self):
        queryset = Product.objects.select_related(
            "vendor", "vendor__user", "category"
        ).prefetch_related("images")

        # For public access, show only active products from approved vendors
        if not self.request.user.is_authenticated or self.action in ["list", "retrieve"]:
            queryset = queryset.filter(
                status=Product.Status.ACTIVE,
                vendor__status="approved",
            )

        return queryset

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ProductDetailSerializer
        if self.action in ["create", "update", "partial_update"]:
            return ProductCreateUpdateSerializer
        return ProductListSerializer

    def get_permissions(self):
        if self.action in ["create"]:
            return [permissions.IsAuthenticated(), IsApprovedVendor()]
        if self.action in ["update", "partial_update", "destroy"]:
            return [permissions.IsAuthenticated(), IsProductOwnerOrAdmin()]
        return super().get_permissions()

    def perform_create(self, serializer):
        product = serializer.save()
        logger.info(
            "Product created: %s by vendor %s",
            product.name,
            product.vendor.store_name,
        )

    def retrieve(self, request, *args, **kwargs):
        """Retrieve product and increment view count."""
        instance = self.get_object()
        Product.objects.filter(pk=instance.pk).update(
            view_count=models.F("view_count") + 1
        )
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def featured(self, request):
        """List featured products."""
        queryset = self.get_queryset().filter(is_featured=True)[:12]
        serializer = ProductListSerializer(
            queryset, many=True, context={"request": request}
        )
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def vendor_products(self, request):
        """List products for the authenticated vendor."""
        if not request.user.is_vendor:
            return Response(
                {"error": "Only vendors can access this endpoint."},
                status=status.HTTP_403_FORBIDDEN,
            )
        queryset = Product.objects.filter(
            vendor=request.user.vendor_profile
        ).select_related("category").prefetch_related("images")
        serializer = ProductListSerializer(
            queryset, many=True, context={"request": request}
        )
        return Response(serializer.data)

    @action(detail=True, methods=["get", "post"])
    def reviews(self, request, slug=None):
        """List or create reviews for a product."""
        product = self.get_object()

        if request.method == "GET":
            reviews = product.reviews.filter(is_approved=True)
            page = self.paginate_queryset(reviews)
            if page is not None:
                serializer = ReviewSerializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            serializer = ReviewSerializer(reviews, many=True)
            return Response(serializer.data)

        if request.method == "POST":
            if not request.user.is_authenticated:
                return Response(
                    {"error": "Authentication required to write a review."},
                    status=status.HTTP_401_UNAUTHORIZED,
                )
            serializer = ReviewCreateSerializer(
                data=request.data,
                context={"request": request, "product": product},
            )
            serializer.is_valid(raise_exception=True)
            review = serializer.save()
            logger.info(
                "Review created for %s by %s (rating: %d)",
                product.name,
                request.user.email,
                review.rating,
            )
            return Response(
                ReviewSerializer(review).data,
                status=status.HTTP_201_CREATED,
            )


class ProductSearchView(generics.ListAPIView):
    """
    Full-text product search using database queries.

    Supports query-based search across product name, description,
    tags, and brand fields. Falls back to database search when
    Elasticsearch is unavailable.
    """

    serializer_class = ProductListSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        query = self.request.query_params.get("q", "").strip()

        if not query:
            return Product.objects.none()

        queryset = Product.objects.filter(
            status=Product.Status.ACTIVE,
            vendor__status="approved",
        ).select_related(
            "vendor", "vendor__user", "category"
        ).prefetch_related("images")

        # Search across multiple fields with relevance weighting
        queryset = queryset.filter(
            Q(name__icontains=query)
            | Q(description__icontains=query)
            | Q(tags__icontains=query)
            | Q(brand__icontains=query)
            | Q(category__name__icontains=query)
            | Q(vendor__store_name__icontains=query)
        ).distinct()

        # Apply optional filters
        min_price = self.request.query_params.get("min_price")
        max_price = self.request.query_params.get("max_price")
        category_slug = self.request.query_params.get("category")
        min_rating = self.request.query_params.get("min_rating")

        if min_price:
            queryset = queryset.filter(price__gte=min_price)
        if max_price:
            queryset = queryset.filter(price__lte=max_price)
        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)
        if min_rating:
            queryset = queryset.filter(average_rating__gte=min_rating)

        # Sorting
        sort_by = self.request.query_params.get("sort", "relevance")
        if sort_by == "price_low":
            queryset = queryset.order_by("price")
        elif sort_by == "price_high":
            queryset = queryset.order_by("-price")
        elif sort_by == "rating":
            queryset = queryset.order_by("-average_rating")
        elif sort_by == "newest":
            queryset = queryset.order_by("-created_at")
        elif sort_by == "popular":
            queryset = queryset.order_by("-total_sold")

        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(
            {
                "query": request.query_params.get("q", ""),
                "count": queryset.count(),
                "results": serializer.data,
            }
        )


class ProductImageDeleteView(generics.DestroyAPIView):
    """Delete a product image (vendor or admin only)."""

    serializer_class = ProductImageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_admin or self.request.user.is_superuser:
            return ProductImage.objects.all()
        return ProductImage.objects.filter(
            product__vendor=self.request.user.vendor_profile
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        product = instance.product
        instance.delete()

        # If deleted image was primary, make the first remaining image primary
        if not product.images.filter(is_primary=True).exists():
            first_image = product.images.first()
            if first_image:
                first_image.is_primary = True
                first_image.save()

        return Response(status=status.HTTP_204_NO_CONTENT)
