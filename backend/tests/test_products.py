"""
Tests for the products application.

Covers product CRUD, category management, review creation,
search functionality, and filtering.
"""

from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from apps.accounts.models import CustomerProfile, User, VendorProfile
from apps.products.models import Category, Product, ProductImage, Review


class CategoryModelTest(TestCase):
    """Tests for the Category model."""

    def setUp(self):
        self.parent = Category.objects.create(
            name="Electronics",
            slug="electronics",
        )
        self.child = Category.objects.create(
            name="Smartphones",
            slug="smartphones",
            parent=self.parent,
        )

    def test_category_str_without_parent(self):
        self.assertEqual(str(self.parent), "Electronics")

    def test_category_str_with_parent(self):
        self.assertEqual(str(self.child), "Electronics > Smartphones")

    def test_full_path(self):
        self.assertEqual(self.child.full_path, "Electronics > Smartphones")

    def test_get_descendants(self):
        grandchild = Category.objects.create(
            name="Android Phones",
            slug="android-phones",
            parent=self.child,
        )
        descendants = self.parent.get_descendants()
        self.assertIn(self.child, descendants)
        self.assertIn(grandchild, descendants)

    def test_auto_slug_generation(self):
        category = Category(name="New Category")
        category.save()
        self.assertEqual(category.slug, "new-category")


class ProductModelTest(TestCase):
    """Tests for the Product model."""

    def setUp(self):
        self.vendor_user = User.objects.create_user(
            email="vendor@test.com",
            password="testpass123",
            first_name="Test",
            last_name="Vendor",
            role=User.Role.VENDOR,
        )
        self.vendor = VendorProfile.objects.create(
            user=self.vendor_user,
            store_name="Test Store",
            slug="test-store",
            status=VendorProfile.Status.APPROVED,
        )
        self.category = Category.objects.create(
            name="Electronics",
            slug="electronics",
        )
        self.product = Product.objects.create(
            vendor=self.vendor,
            category=self.category,
            name="Test Product",
            slug="test-product",
            description="A test product description.",
            price=Decimal("99.99"),
            sku="TEST-001",
            stock_quantity=50,
        )

    def test_product_str(self):
        self.assertEqual(str(self.product), "Test Product")

    def test_is_in_stock_with_quantity(self):
        self.assertTrue(self.product.is_in_stock)

    def test_is_in_stock_zero_quantity(self):
        self.product.stock_quantity = 0
        self.product.save()
        self.assertFalse(self.product.is_in_stock)

    def test_is_low_stock(self):
        self.product.stock_quantity = 5
        self.product.save()
        self.assertTrue(self.product.is_low_stock)

    def test_discount_percentage(self):
        self.product.compare_at_price = Decimal("149.99")
        self.product.save()
        expected = round(
            ((Decimal("149.99") - Decimal("99.99")) / Decimal("149.99")) * 100,
            1,
        )
        self.assertEqual(self.product.discount_percentage, expected)

    def test_discount_percentage_no_compare_price(self):
        self.assertEqual(self.product.discount_percentage, 0)

    def test_decrement_stock_success(self):
        result = self.product.decrement_stock(10)
        self.assertTrue(result)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 40)
        self.assertEqual(self.product.total_sold, 10)

    def test_decrement_stock_insufficient(self):
        result = self.product.decrement_stock(100)
        self.assertFalse(result)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 50)

    def test_increment_stock(self):
        self.product.increment_stock(20)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 70)

    def test_auto_slug_generation(self):
        product = Product(
            vendor=self.vendor,
            name="Another Product",
            description="Description",
            price=Decimal("29.99"),
            sku="TEST-002",
        )
        product.save()
        self.assertEqual(product.slug, "another-product")

    def test_auto_out_of_stock_status(self):
        self.product.stock_quantity = 0
        self.product.status = Product.Status.ACTIVE
        self.product.save()
        self.assertEqual(self.product.status, Product.Status.OUT_OF_STOCK)


class ProductAPITest(APITestCase):
    """Tests for Product API endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.customer_user = User.objects.create_user(
            email="customer@test.com",
            password="testpass123",
            first_name="Test",
            last_name="Customer",
            role=User.Role.CUSTOMER,
        )
        CustomerProfile.objects.create(user=self.customer_user)

        self.vendor_user = User.objects.create_user(
            email="vendor@test.com",
            password="testpass123",
            first_name="Test",
            last_name="Vendor",
            role=User.Role.VENDOR,
        )
        self.vendor = VendorProfile.objects.create(
            user=self.vendor_user,
            store_name="Test Store",
            slug="test-store",
            status=VendorProfile.Status.APPROVED,
        )
        self.category = Category.objects.create(
            name="Electronics",
            slug="electronics",
        )
        self.product = Product.objects.create(
            vendor=self.vendor,
            category=self.category,
            name="Test Product",
            slug="test-product",
            description="A test product.",
            price=Decimal("99.99"),
            sku="TEST-001",
            stock_quantity=50,
            status=Product.Status.ACTIVE,
        )

    def test_list_products_unauthenticated(self):
        url = reverse("products:product-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_product_detail(self):
        url = reverse("products:product-detail", kwargs={"slug": "test-product"})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Test Product")

    def test_create_product_as_vendor(self):
        self.client.force_authenticate(user=self.vendor_user)
        url = reverse("products:product-list")
        data = {
            "name": "New Product",
            "description": "Brand new product.",
            "price": "49.99",
            "sku": "NEW-001",
            "stock_quantity": 100,
            "status": "active",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Product.objects.count(), 2)

    def test_create_product_as_customer_forbidden(self):
        self.client.force_authenticate(user=self.customer_user)
        url = reverse("products:product-list")
        data = {
            "name": "New Product",
            "description": "Brand new product.",
            "price": "49.99",
            "sku": "NEW-001",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class ReviewModelTest(TestCase):
    """Tests for the Review model."""

    def setUp(self):
        self.vendor_user = User.objects.create_user(
            email="vendor@test.com",
            password="testpass123",
            first_name="Vendor",
            last_name="User",
            role=User.Role.VENDOR,
        )
        self.vendor = VendorProfile.objects.create(
            user=self.vendor_user,
            store_name="Test Store",
            slug="test-store",
            status=VendorProfile.Status.APPROVED,
        )
        self.customer = User.objects.create_user(
            email="customer@test.com",
            password="testpass123",
            first_name="Customer",
            last_name="User",
            role=User.Role.CUSTOMER,
        )
        self.product = Product.objects.create(
            vendor=self.vendor,
            name="Test Product",
            slug="test-product",
            description="Description",
            price=Decimal("29.99"),
            sku="TEST-001",
        )

    def test_review_updates_product_rating(self):
        Review.objects.create(
            product=self.product,
            user=self.customer,
            rating=4,
            title="Great product",
            comment="Really liked it.",
        )
        self.product.refresh_from_db()
        self.assertEqual(self.product.average_rating, 4)
        self.assertEqual(self.product.review_count, 1)

    def test_unique_review_per_product_per_user(self):
        Review.objects.create(
            product=self.product,
            user=self.customer,
            rating=4,
            title="First review",
            comment="Comment",
        )
        with self.assertRaises(Exception):
            Review.objects.create(
                product=self.product,
                user=self.customer,
                rating=5,
                title="Second review",
                comment="Another comment",
            )
