"""
Serializers for the products application.

Handles product listing, detail, creation, and review serialization
with optimized nested representations.
"""

from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.accounts.serializers import VendorListSerializer

from .models import Category, Product, ProductImage, Review

User = get_user_model()


class CategorySerializer(serializers.ModelSerializer):
    """Serializer for product categories."""

    children = serializers.SerializerMethodField()
    product_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "image",
            "parent",
            "children",
            "product_count",
            "is_active",
            "sort_order",
        ]

    def get_children(self, obj):
        children = obj.children.filter(is_active=True)
        return CategorySerializer(children, many=True).data

    def get_product_count(self, obj):
        return obj.products.filter(status=Product.Status.ACTIVE).count()


class CategoryListSerializer(serializers.ModelSerializer):
    """Simplified category serializer for use in product lists."""

    class Meta:
        model = Category
        fields = ["id", "name", "slug"]


class ProductImageSerializer(serializers.ModelSerializer):
    """Serializer for product images."""

    class Meta:
        model = ProductImage
        fields = ["id", "image", "alt_text", "is_primary", "sort_order"]
        read_only_fields = ["id"]


class ReviewSerializer(serializers.ModelSerializer):
    """Serializer for product reviews."""

    user_name = serializers.CharField(source="user.full_name", read_only=True)
    user_avatar = serializers.ImageField(source="user.avatar", read_only=True)

    class Meta:
        model = Review
        fields = [
            "id",
            "user_name",
            "user_avatar",
            "rating",
            "title",
            "comment",
            "is_verified_purchase",
            "helpful_count",
            "not_helpful_count",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "is_verified_purchase",
            "helpful_count",
            "not_helpful_count",
            "created_at",
        ]


class ReviewCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating product reviews."""

    class Meta:
        model = Review
        fields = ["rating", "title", "comment"]

    def validate(self, attrs):
        request = self.context["request"]
        product = self.context["product"]

        # Check if user already reviewed this product
        if Review.objects.filter(product=product, user=request.user).exists():
            raise serializers.ValidationError(
                "You have already reviewed this product."
            )

        # Check if user is the product vendor (vendors cannot review own products)
        if hasattr(request.user, "vendor_profile"):
            if product.vendor == request.user.vendor_profile:
                raise serializers.ValidationError(
                    "Vendors cannot review their own products."
                )

        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        product = self.context["product"]

        # Check if this is a verified purchase
        is_verified = product.order_items.filter(
            order__customer=request.user,
            order__status__in=["delivered", "completed"],
        ).exists()

        review = Review.objects.create(
            product=product,
            user=request.user,
            is_verified_purchase=is_verified,
            **validated_data,
        )
        return review


class ProductListSerializer(serializers.ModelSerializer):
    """
    Serializer for product list views.

    Optimized with minimal data for fast loading of product grids.
    """

    category = CategoryListSerializer(read_only=True)
    vendor_name = serializers.CharField(
        source="vendor.store_name", read_only=True
    )
    vendor_slug = serializers.CharField(source="vendor.slug", read_only=True)
    primary_image = serializers.SerializerMethodField()
    discount_percentage = serializers.ReadOnlyField()
    is_in_stock = serializers.ReadOnlyField()

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "slug",
            "short_description",
            "price",
            "compare_at_price",
            "discount_percentage",
            "category",
            "vendor_name",
            "vendor_slug",
            "primary_image",
            "average_rating",
            "review_count",
            "is_in_stock",
            "is_featured",
            "created_at",
        ]

    def get_primary_image(self, obj):
        image = obj.primary_image
        if image:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(image.image.url)
            return image.image.url
        return None


class ProductDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for product detail views.

    Includes all product information, images, vendor details, and reviews.
    """

    category = CategorySerializer(read_only=True)
    vendor = VendorListSerializer(read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    reviews = serializers.SerializerMethodField()
    discount_percentage = serializers.ReadOnlyField()
    is_in_stock = serializers.ReadOnlyField()
    is_low_stock = serializers.ReadOnlyField()

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "short_description",
            "price",
            "compare_at_price",
            "discount_percentage",
            "sku",
            "stock_quantity",
            "is_in_stock",
            "is_low_stock",
            "weight",
            "tags",
            "brand",
            "category",
            "vendor",
            "images",
            "reviews",
            "average_rating",
            "review_count",
            "total_sold",
            "is_featured",
            "created_at",
            "updated_at",
        ]

    def get_reviews(self, obj):
        """Return the latest 5 approved reviews."""
        reviews = obj.reviews.filter(is_approved=True)[:5]
        return ReviewSerializer(reviews, many=True).data


class ProductCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating and updating products (vendor use).

    Handles image uploads through nested serialization.
    """

    images = ProductImageSerializer(many=True, required=False, read_only=True)
    uploaded_images = serializers.ListField(
        child=serializers.ImageField(),
        write_only=True,
        required=False,
    )
    category_id = serializers.UUIDField(write_only=True, required=False)

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "short_description",
            "price",
            "compare_at_price",
            "sku",
            "stock_quantity",
            "low_stock_threshold",
            "track_inventory",
            "weight",
            "tags",
            "brand",
            "status",
            "is_featured",
            "category_id",
            "images",
            "uploaded_images",
        ]
        read_only_fields = ["id", "slug"]

    def validate_sku(self, value):
        """Ensure SKU is unique (excluding current instance on update)."""
        queryset = Product.objects.filter(sku=value)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError("A product with this SKU already exists.")
        return value

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Price must be greater than zero.")
        return value

    def validate(self, attrs):
        compare_price = attrs.get(
            "compare_at_price",
            getattr(self.instance, "compare_at_price", None),
        )
        price = attrs.get("price", getattr(self.instance, "price", None))

        if compare_price and price and compare_price <= price:
            raise serializers.ValidationError(
                {"compare_at_price": "Compare-at price must be greater than the selling price."}
            )
        return attrs

    def create(self, validated_data):
        uploaded_images = validated_data.pop("uploaded_images", [])
        category_id = validated_data.pop("category_id", None)

        if category_id:
            try:
                validated_data["category"] = Category.objects.get(id=category_id)
            except Category.DoesNotExist:
                raise serializers.ValidationError(
                    {"category_id": "Category not found."}
                )

        # Set vendor from the request user
        request = self.context["request"]
        validated_data["vendor"] = request.user.vendor_profile

        product = Product.objects.create(**validated_data)

        # Create product images
        for i, image in enumerate(uploaded_images):
            ProductImage.objects.create(
                product=product,
                image=image,
                is_primary=(i == 0),
                sort_order=i,
            )

        return product

    def update(self, instance, validated_data):
        uploaded_images = validated_data.pop("uploaded_images", [])
        category_id = validated_data.pop("category_id", None)

        if category_id:
            try:
                validated_data["category"] = Category.objects.get(id=category_id)
            except Category.DoesNotExist:
                raise serializers.ValidationError(
                    {"category_id": "Category not found."}
                )

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Add new images (do not remove existing ones)
        if uploaded_images:
            existing_count = instance.images.count()
            for i, image in enumerate(uploaded_images):
                ProductImage.objects.create(
                    product=instance,
                    image=image,
                    sort_order=existing_count + i,
                )

        return instance
