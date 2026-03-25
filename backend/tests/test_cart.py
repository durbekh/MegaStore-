"""
Tests for the cart application.

Covers cart operations: adding items, updating quantities,
removing items, clearing cart, and stock validation.
"""

from decimal import Decimal

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from apps.accounts.models import CustomerProfile, User, VendorProfile
from apps.cart.models import Cart, CartItem
from apps.products.models import Product


class CartModelTest(TestCase):
    """Tests for the Cart and CartItem models."""

    def setUp(self):
        self.customer = User.objects.create_user(
            email="customer@test.com",
            password="testpass123",
            first_name="Test",
            last_name="Customer",
            role=User.Role.CUSTOMER,
        )
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
        self.product1 = Product.objects.create(
            vendor=self.vendor,
            name="Product One",
            slug="product-one",
            description="First product",
            price=Decimal("25.00"),
            sku="PROD-001",
            stock_quantity=50,
            status=Product.Status.ACTIVE,
        )
        self.product2 = Product.objects.create(
            vendor=self.vendor,
            name="Product Two",
            slug="product-two",
            description="Second product",
            price=Decimal("15.50"),
            sku="PROD-002",
            stock_quantity=30,
            status=Product.Status.ACTIVE,
        )
        self.cart = Cart.objects.create(user=self.customer)

    def test_cart_str(self):
        self.assertEqual(str(self.cart), "Cart for customer@test.com")

    def test_total_items_empty(self):
        self.assertEqual(self.cart.total_items, 0)
        self.assertEqual(self.cart.total_unique_items, 0)

    def test_add_items_and_totals(self):
        CartItem.objects.create(cart=self.cart, product=self.product1, quantity=2)
        CartItem.objects.create(cart=self.cart, product=self.product2, quantity=3)
        self.assertEqual(self.cart.total_items, 5)
        self.assertEqual(self.cart.total_unique_items, 2)

    def test_subtotal(self):
        CartItem.objects.create(cart=self.cart, product=self.product1, quantity=2)
        CartItem.objects.create(cart=self.cart, product=self.product2, quantity=1)
        expected = Decimal("25.00") * 2 + Decimal("15.50") * 1
        self.assertEqual(self.cart.subtotal, expected)

    def test_clear_cart(self):
        CartItem.objects.create(cart=self.cart, product=self.product1, quantity=1)
        CartItem.objects.create(cart=self.cart, product=self.product2, quantity=1)
        self.cart.clear()
        self.assertEqual(self.cart.items.count(), 0)

    def test_cart_item_line_total(self):
        item = CartItem.objects.create(
            cart=self.cart, product=self.product1, quantity=4
        )
        self.assertEqual(item.line_total, Decimal("100.00"))

    def test_cart_item_is_available(self):
        item = CartItem.objects.create(
            cart=self.cart, product=self.product1, quantity=5
        )
        self.assertTrue(item.is_available)

    def test_cart_item_not_available_over_stock(self):
        item = CartItem.objects.create(
            cart=self.cart, product=self.product1, quantity=100
        )
        self.assertFalse(item.is_available)

    def test_unique_product_per_cart(self):
        CartItem.objects.create(cart=self.cart, product=self.product1, quantity=1)
        with self.assertRaises(Exception):
            CartItem.objects.create(
                cart=self.cart, product=self.product1, quantity=2
            )

    def test_get_items_by_vendor(self):
        CartItem.objects.create(cart=self.cart, product=self.product1, quantity=1)
        CartItem.objects.create(cart=self.cart, product=self.product2, quantity=1)
        groups = self.cart.get_items_by_vendor()
        self.assertEqual(len(groups), 1)
        vendor_group = groups[self.vendor.id]
        self.assertEqual(vendor_group["vendor_name"], "Test Store")
        self.assertEqual(len(vendor_group["items"]), 2)


class CartAPITest(APITestCase):
    """Tests for Cart API endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.customer = User.objects.create_user(
            email="customer@test.com",
            password="testpass123",
            first_name="Test",
            last_name="Customer",
            role=User.Role.CUSTOMER,
        )
        CustomerProfile.objects.create(user=self.customer)
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
        self.product = Product.objects.create(
            vendor=self.vendor,
            name="Cart Product",
            slug="cart-product",
            description="Product for cart testing",
            price=Decimal("19.99"),
            sku="CART-001",
            stock_quantity=10,
            status=Product.Status.ACTIVE,
        )

    def test_get_cart_creates_if_not_exists(self):
        self.client.force_authenticate(user=self.customer)
        response = self.client.get("/api/cart/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(Cart.objects.filter(user=self.customer).exists())

    def test_add_item_to_cart(self):
        self.client.force_authenticate(user=self.customer)
        data = {"product_id": str(self.product.id), "quantity": 2}
        response = self.client.post("/api/cart/items/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_items"], 2)

    def test_add_item_unauthenticated(self):
        data = {"product_id": str(self.product.id), "quantity": 1}
        response = self.client.post("/api/cart/items/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_cart_summary(self):
        self.client.force_authenticate(user=self.customer)
        cart = Cart.objects.create(user=self.customer)
        CartItem.objects.create(cart=cart, product=self.product, quantity=3)
        response = self.client.get("/api/cart/summary/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_items"], 3)

    def test_clear_cart(self):
        self.client.force_authenticate(user=self.customer)
        cart = Cart.objects.create(user=self.customer)
        CartItem.objects.create(cart=cart, product=self.product, quantity=1)
        response = self.client.post("/api/cart/clear/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(cart.items.count(), 0)
