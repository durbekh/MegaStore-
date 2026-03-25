"""
Filters for the products application.

Provides advanced filtering capabilities for product listings
using django-filter.
"""

import django_filters
from django.db.models import Q

from .models import Product


class ProductFilter(django_filters.FilterSet):
    """
    Filter set for product queries.

    Supports filtering by:
    - Category (slug)
    - Price range (min/max)
    - Rating (minimum)
    - Vendor (slug)
    - Brand
    - Availability (in stock)
    - Featured status
    - Search query
    """

    category = django_filters.CharFilter(
        field_name="category__slug",
        lookup_expr="exact",
        label="Category slug",
    )
    min_price = django_filters.NumberFilter(
        field_name="price",
        lookup_expr="gte",
        label="Minimum price",
    )
    max_price = django_filters.NumberFilter(
        field_name="price",
        lookup_expr="lte",
        label="Maximum price",
    )
    min_rating = django_filters.NumberFilter(
        field_name="average_rating",
        lookup_expr="gte",
        label="Minimum rating",
    )
    vendor = django_filters.CharFilter(
        field_name="vendor__slug",
        lookup_expr="exact",
        label="Vendor slug",
    )
    brand = django_filters.CharFilter(
        field_name="brand",
        lookup_expr="icontains",
        label="Brand name",
    )
    in_stock = django_filters.BooleanFilter(
        method="filter_in_stock",
        label="In stock only",
    )
    is_featured = django_filters.BooleanFilter(
        field_name="is_featured",
        label="Featured only",
    )
    tags = django_filters.CharFilter(
        method="filter_by_tags",
        label="Tags (comma-separated)",
    )
    q = django_filters.CharFilter(
        method="filter_search",
        label="Search query",
    )

    class Meta:
        model = Product
        fields = [
            "category",
            "min_price",
            "max_price",
            "min_rating",
            "vendor",
            "brand",
            "in_stock",
            "is_featured",
            "tags",
            "q",
        ]

    def filter_in_stock(self, queryset, name, value):
        """Filter products that are in stock."""
        if value:
            return queryset.filter(
                Q(track_inventory=False) | Q(stock_quantity__gt=0)
            )
        return queryset

    def filter_by_tags(self, queryset, name, value):
        """Filter products by comma-separated tags."""
        tags = [tag.strip() for tag in value.split(",") if tag.strip()]
        query = Q()
        for tag in tags:
            query |= Q(tags__icontains=tag)
        return queryset.filter(query)

    def filter_search(self, queryset, name, value):
        """Full-text search across multiple product fields."""
        if not value:
            return queryset
        return queryset.filter(
            Q(name__icontains=value)
            | Q(description__icontains=value)
            | Q(tags__icontains=value)
            | Q(brand__icontains=value)
        ).distinct()
