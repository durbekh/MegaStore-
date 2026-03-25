"""
Views for the accounts application.

Handles user registration, authentication, profile management,
and address CRUD operations.
"""

import logging

from django.contrib.auth import get_user_model
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .models import Address, CustomerProfile, VendorProfile
from .permissions import IsAccountOwner, IsAdminUser, IsVendor
from .serializers import (
    AddressSerializer,
    ChangePasswordSerializer,
    CustomerProfileSerializer,
    CustomerRegistrationSerializer,
    CustomTokenObtainPairSerializer,
    UserProfileUpdateSerializer,
    UserSerializer,
    VendorListSerializer,
    VendorProfileSerializer,
    VendorRegistrationSerializer,
)
from .tasks import send_welcome_email

logger = logging.getLogger(__name__)

User = get_user_model()


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Obtain JWT access and refresh tokens.

    Returns token pair along with user profile data.
    """

    serializer_class = CustomTokenObtainPairSerializer


class CustomerRegistrationView(generics.CreateAPIView):
    """
    Register a new customer account.

    Creates a user with CUSTOMER role and an associated customer profile.
    Returns JWT tokens for immediate login after registration.
    """

    serializer_class = CustomerRegistrationSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)

        # Send welcome email asynchronously
        send_welcome_email.delay(user.id)

        logger.info("New customer registered: %s", user.email)

        return Response(
            {
                "message": "Registration successful.",
                "user": UserSerializer(user).data,
                "tokens": {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                },
            },
            status=status.HTTP_201_CREATED,
        )


class VendorRegistrationView(generics.CreateAPIView):
    """
    Register a new vendor account.

    Creates a user with VENDOR role and an associated vendor profile.
    Vendor profile starts in PENDING status until admin approval.
    """

    serializer_class = VendorRegistrationSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        refresh = RefreshToken.for_user(user)

        send_welcome_email.delay(user.id)

        logger.info("New vendor registered: %s (store: %s)", user.email, user.vendor_profile.store_name)

        return Response(
            {
                "message": "Vendor registration successful. Your account is pending approval.",
                "user": UserSerializer(user).data,
                "vendor": VendorProfileSerializer(user.vendor_profile).data,
                "tokens": {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                },
            },
            status=status.HTTP_201_CREATED,
        )


class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    Retrieve or update the authenticated user's profile.

    GET: Returns user profile with role-specific details.
    PATCH/PUT: Updates basic user information.
    """

    serializer_class = UserProfileUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_object(self):
        return self.request.user

    def retrieve(self, request, *args, **kwargs):
        user = self.get_object()
        data = UserSerializer(user).data

        # Include role-specific profile
        if user.is_vendor:
            try:
                data["vendor_profile"] = VendorProfileSerializer(
                    user.vendor_profile
                ).data
            except VendorProfile.DoesNotExist:
                data["vendor_profile"] = None
        elif user.is_customer:
            try:
                data["customer_profile"] = CustomerProfileSerializer(
                    user.customer_profile
                ).data
            except CustomerProfile.DoesNotExist:
                data["customer_profile"] = None

        return Response(data)


class ChangePasswordView(APIView):
    """Change the authenticated user's password."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        user = request.user
        user.set_password(serializer.validated_data["new_password"])
        user.save()

        logger.info("Password changed for user: %s", user.email)

        return Response(
            {"message": "Password changed successfully."},
            status=status.HTTP_200_OK,
        )


class LogoutView(APIView):
    """
    Logout by blacklisting the refresh token.

    Prevents the refresh token from being used to obtain new access tokens.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            if not refresh_token:
                return Response(
                    {"error": "Refresh token is required."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response(
                {"message": "Logged out successfully."},
                status=status.HTTP_200_OK,
            )
        except Exception:
            return Response(
                {"error": "Invalid token."},
                status=status.HTTP_400_BAD_REQUEST,
            )


class AddressViewSet(viewsets.ModelViewSet):
    """
    CRUD operations for user addresses.

    Allows authenticated users to manage their shipping
    and billing addresses.
    """

    serializer_class = AddressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

    @action(detail=True, methods=["post"])
    def set_default(self, request, pk=None):
        """Set an address as the default."""
        address = self.get_object()
        address.is_default = True
        address.save()
        return Response(
            {"message": "Address set as default."},
            status=status.HTTP_200_OK,
        )


class VendorProfileUpdateView(generics.RetrieveUpdateAPIView):
    """
    View for vendors to manage their store profile.

    Only accessible by users with the VENDOR role.
    """

    serializer_class = VendorProfileSerializer
    permission_classes = [permissions.IsAuthenticated, IsVendor]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_object(self):
        return self.request.user.vendor_profile


class CustomerProfileUpdateView(generics.RetrieveUpdateAPIView):
    """View for customers to manage their profile."""

    serializer_class = CustomerProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user.customer_profile


class VendorListView(generics.ListAPIView):
    """
    List all approved vendors (public).

    Returns a paginated list of vendor stores with basic information.
    """

    serializer_class = VendorListSerializer
    permission_classes = [permissions.AllowAny]
    queryset = VendorProfile.objects.filter(
        status=VendorProfile.Status.APPROVED
    ).select_related("user")


class VendorDetailView(generics.RetrieveAPIView):
    """
    Retrieve a single vendor's public profile by slug.
    """

    serializer_class = VendorProfileSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = "slug"
    queryset = VendorProfile.objects.filter(
        status=VendorProfile.Status.APPROVED
    ).select_related("user")


class AdminVendorApprovalView(APIView):
    """
    Admin endpoint to approve or reject vendor registrations.
    """

    permission_classes = [permissions.IsAuthenticated, IsAdminUser]

    def post(self, request, vendor_id):
        try:
            vendor = VendorProfile.objects.get(id=vendor_id)
        except VendorProfile.DoesNotExist:
            return Response(
                {"error": "Vendor not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        action_type = request.data.get("action")
        reason = request.data.get("reason", "")

        if action_type == "approve":
            vendor.approve()
            logger.info("Vendor approved: %s", vendor.store_name)
            return Response({"message": f"Vendor '{vendor.store_name}' approved."})
        elif action_type == "reject":
            vendor.reject(reason)
            logger.info("Vendor rejected: %s (reason: %s)", vendor.store_name, reason)
            return Response({"message": f"Vendor '{vendor.store_name}' rejected."})
        elif action_type == "suspend":
            vendor.suspend(reason)
            logger.info("Vendor suspended: %s", vendor.store_name)
            return Response({"message": f"Vendor '{vendor.store_name}' suspended."})
        else:
            return Response(
                {"error": "Invalid action. Use 'approve', 'reject', or 'suspend'."},
                status=status.HTTP_400_BAD_REQUEST,
            )
