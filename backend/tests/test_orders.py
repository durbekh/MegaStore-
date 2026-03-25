"""
Tests for the orders application.

Covers order creation, lifecycle management, cancellation,
vendor fulfillment, and order number generation.
"""

from decimal import Decimal

from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from apps.accounts.models import CustomerProfile, User, VendorProfile
from apps.cart.models import Cart, CartItem
from apps.orders.models import Order, OrderItem
from apps.products.models import Product


@override_settings(PLATFORM_FEE_PERCENT=5.0)
class OrderModelTest(TestCase):
    """Tests for the Order model."""

    def setUp(self):
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
        self.product = Product.objects.create(
            vendor=self.vendor,
            name="Test Product",
            slug="test-product",
            description="Description",
            price=Decimal("50.00"),
            sku="TEST-001",
            stock_quantity=100,
            status=Product.Status.ACTIVE,
        )

    def _create_order(self, **kwargs):
        """Helper to create an order with default values."""
        defaults = {
            "customer": self.customer,
            "subtotal": Decimal("100.00"),
            "shipping_cost": Decimal("5.99"),
            "tax_amount": Decimal("5.00"),
            "total_amount": Decimal("110.99"),
            "shipping_full_name": "Test Customer",
            "shipping_address_line1": "123 Test St",
            "shipping_city": "Test City",
            "shipping_state": "CA",
            "shipping_postal_code": "90210",
            "shipping_country": "US",
        }
        defaults.update(kwargs)
        return Order.objects.create(**defaults)

    def test_order_number_generation(self):
        order = self._create_order()
        self.assertTrue(order.order_number.startswith("MS"))
        self.assertEqual(len(order.order_number), 13)

    def test_order_number_sequential(self):
        order1 = self._create_order()
        order2 = self._create_order()
        num1 = int(order1.order_number[-5:])
        num2 = int(order2.order_number[-5:])
        self.assertEqual(num2, num1 + 1)

    def test_order_str(self):
        order = self._create_order()
        self.assertTrue(str(order).startswith("Order MS"))

    def test_cancel_pending_order(self):
        order = self._create_order(status=Order.Status.PENDING)
        item = OrderItem.objects.create(
            order=order,
            product=self.product,
            vendor=self.vendor,
            product_name="Test Product",
            product_sku="TEST-001",
            unit_price=Decimal("50.00"),
            quantity=2,
        )
        self.product.decrement_stock(2)

        order.cancel()
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.CANCELLED)

        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 100)

    def test_cancel_shipped_order_raises(self):
        order = self._create_order(status=Order.Status.SHIPPED)
        with self.assertRaises(ValueError):
            order.cancel()

    def test_can_cancel_pending(self):
        order = self._create_order(status=Order.Status.PENDING)
        self.assertTrue(order.can_cancel)

    def test_cannot_cancel_delivered(self):
        order = self._create_order(status=Order.Status.DELIVERED)
        self.assertFalse(order.can_cancel)

    def test_mark_shipped(self):
        order = self._create_order(status=Order.Status.CONFIRMED)
        order.mark_shipped(tracking_number="TRACK123")
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.SHIPPED)
        self.assertEqual(order.tracking_number, "TRACK123")
        self.assertIsNotNone(order.shipped_at)

    def test_mark_delivered(self):
        order = self._create_order(status=Order.Status.SHIPPED)
        order.mark_delivered()
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.DELIVERED)
        self.assertIsNotNone(order.delivered_at)

    def test_confirm_payment(self):
        order = self._create_order()
        order.confirm_payment("pi_test_123")
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.CONFIRMED)
        self.assertEqual(order.payment_status, "paid")
        self.assertEqual(order.stripe_payment_intent_id, "pi_test_123")
        self.assertIsNotNone(order.paid_at)

    def test_vendor_ids(self):
        order = self._create_order()
        OrderItem.objects.create(
            order=order,
            product=self.product,
            vendor=self.vendor,
            product_name="Test Product",
            product_sku="TEST-001",
            unit_price=Decimal("50.00"),
            quantity=1,
        )
        self.assertIn(self.vendor.id, order.vendor_ids)


class OrderItemModelTest(TestCase):
    """Tests for the OrderItem model."""

    def setUp(self):
        self.customer = User.objects.create_user(
            email="customer@test.com",
            password="testpass123",
            first_name="Test",
            last_name="Customer",
        )
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
        )
        self.product = Product.objects.create(
            vendor=self.vendor,
            name="Test Product",
            slug="test-product",
            description="Desc",
            price=Decimal("25.00"),
            sku="ITEM-001",
        )
        self.order = Order.objects.create(
            customer=self.customer,
            subtotal=Decimal("75.00"),
            total_amount=Decimal("80.00"),
            shipping_full_name="Test",
            shipping_address_line1="123 St",
            shipping_city="City",
            shipping_state="CA",
            shipping_postal_code="90210",
        )
        self.item = OrderItem.objects.create(
            order=self.order,
            product=self.product,
            vendor=self.vendor,
            product_name="Test Product",
            product_sku="ITEM-001",
            unit_price=Decimal("25.00"),
            quantity=3,
        )

    def test_total_price(self):
        self.assertEqual(self.item.total_price, Decimal("75.00"))

    def test_fulfill(self):
        self.item.fulfill()
        self.item.refresh_from_db()
        self.assertTrue(self.item.is_fulfilled)
        self.assertIsNotNone(self.item.fulfilled_at)

    def test_str(self):
        self.assertIn("3x Test Product", str(self.item))
