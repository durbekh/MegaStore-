"""
Tests for the accounts application.

Covers user registration, authentication, profile management,
permissions, and address operations.
"""

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from apps.accounts.models import Address, CustomerProfile, User, VendorProfile


class UserModelTest(TestCase):
    """Tests for the custom User model."""

    def test_create_customer(self):
        user = User.objects.create_user(
            email="customer@test.com",
            password="securepass123",
            first_name="Jane",
            last_name="Doe",
            role=User.Role.CUSTOMER,
        )
        self.assertEqual(user.email, "customer@test.com")
        self.assertTrue(user.check_password("securepass123"))
        self.assertTrue(user.is_customer)
        self.assertFalse(user.is_vendor)
        self.assertFalse(user.is_staff)

    def test_create_vendor(self):
        user = User.objects.create_user(
            email="vendor@test.com",
            password="securepass123",
            first_name="John",
            last_name="Vendor",
            role=User.Role.VENDOR,
        )
        self.assertTrue(user.is_vendor)
        self.assertFalse(user.is_customer)

    def test_create_superuser(self):
        user = User.objects.create_superuser(
            email="admin@test.com",
            password="adminpass123",
            first_name="Admin",
            last_name="User",
        )
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertEqual(user.role, User.Role.ADMIN)

    def test_full_name(self):
        user = User.objects.create_user(
            email="user@test.com",
            password="pass123",
            first_name="Alice",
            last_name="Smith",
        )
        self.assertEqual(user.full_name, "Alice Smith")

    def test_email_required(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(email="", password="pass123")

    def test_user_str(self):
        user = User.objects.create_user(
            email="user@test.com",
            password="pass123",
            first_name="Bob",
            last_name="Jones",
        )
        self.assertEqual(str(user), "Bob Jones (user@test.com)")

    def test_email_normalized(self):
        user = User.objects.create_user(
            email="User@EXAMPLE.COM",
            password="pass123",
            first_name="Test",
            last_name="User",
        )
        self.assertEqual(user.email, "User@example.com")


class VendorProfileModelTest(TestCase):
    """Tests for the VendorProfile model."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="vendor@test.com",
            password="pass123",
            first_name="Vendor",
            last_name="User",
            role=User.Role.VENDOR,
        )
        self.vendor = VendorProfile.objects.create(
            user=self.user,
            store_name="My Store",
            slug="my-store",
        )

    def test_vendor_starts_pending(self):
        self.assertEqual(self.vendor.status, VendorProfile.Status.PENDING)
        self.assertFalse(self.vendor.is_approved)

    def test_approve_vendor(self):
        self.vendor.approve()
        self.vendor.refresh_from_db()
        self.assertEqual(self.vendor.status, VendorProfile.Status.APPROVED)
        self.assertTrue(self.vendor.is_approved)
        self.assertIsNotNone(self.vendor.approved_at)

    def test_reject_vendor(self):
        self.vendor.reject("Incomplete documents")
        self.vendor.refresh_from_db()
        self.assertEqual(self.vendor.status, VendorProfile.Status.REJECTED)
        self.assertEqual(self.vendor.rejection_reason, "Incomplete documents")

    def test_suspend_vendor(self):
        self.vendor.approve()
        self.vendor.suspend("Policy violation")
        self.vendor.refresh_from_db()
        self.assertEqual(self.vendor.status, VendorProfile.Status.SUSPENDED)


class AuthenticationAPITest(APITestCase):
    """Tests for authentication endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="user@test.com",
            password="testpass123",
            first_name="Test",
            last_name="User",
            role=User.Role.CUSTOMER,
        )
        CustomerProfile.objects.create(user=self.user)

    def test_customer_registration(self):
        url = reverse("accounts:customer-register")
        data = {
            "email": "newcustomer@test.com",
            "first_name": "New",
            "last_name": "Customer",
            "password": "StrongPass123!",
            "password_confirm": "StrongPass123!",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("tokens", response.data)
        self.assertTrue(
            User.objects.filter(email="newcustomer@test.com").exists()
        )

    def test_registration_passwords_mismatch(self):
        url = reverse("accounts:customer-register")
        data = {
            "email": "mismatch@test.com",
            "first_name": "Test",
            "last_name": "User",
            "password": "StrongPass123!",
            "password_confirm": "DifferentPass456!",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_registration_duplicate_email(self):
        url = reverse("accounts:customer-register")
        data = {
            "email": "user@test.com",
            "first_name": "Dup",
            "last_name": "User",
            "password": "StrongPass123!",
            "password_confirm": "StrongPass123!",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_success(self):
        url = reverse("accounts:login")
        data = {"email": "user@test.com", "password": "testpass123"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_login_wrong_password(self):
        url = reverse("accounts:login")
        data = {"email": "user@test.com", "password": "wrongpassword"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_profile_authenticated(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("accounts:user-profile")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "user@test.com")

    def test_profile_unauthenticated(self):
        url = reverse("accounts:user-profile")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AddressModelTest(TestCase):
    """Tests for the Address model."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="user@test.com",
            password="pass123",
            first_name="Test",
            last_name="User",
        )

    def test_create_address(self):
        address = Address.objects.create(
            user=self.user,
            label="Home",
            full_name="Test User",
            address_line1="123 Main St",
            city="Springfield",
            state="IL",
            postal_code="62704",
            country="US",
            is_default=True,
        )
        self.assertEqual(str(address), "Home: 123 Main St, Springfield")
        self.assertTrue(address.is_default)

    def test_only_one_default_per_user(self):
        addr1 = Address.objects.create(
            user=self.user,
            label="Home",
            full_name="Test User",
            address_line1="123 Main St",
            city="City",
            state="ST",
            postal_code="12345",
            is_default=True,
        )
        addr2 = Address.objects.create(
            user=self.user,
            label="Office",
            full_name="Test User",
            address_line1="456 Work Rd",
            city="City",
            state="ST",
            postal_code="12345",
            is_default=True,
        )
        addr1.refresh_from_db()
        self.assertFalse(addr1.is_default)
        self.assertTrue(addr2.is_default)
