"""
Serializers for the accounts application.

Handles user registration, authentication, profile management,
and address serialization with comprehensive validation.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django.utils.text import slugify
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import Address, CustomerProfile, VendorProfile

User = get_user_model()


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom JWT token serializer that includes user role and profile
    information in the token claims.
    """

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["email"] = user.email
        token["role"] = user.role
        token["full_name"] = user.full_name
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data["user"] = UserSerializer(self.user).data
        return data


class UserSerializer(serializers.ModelSerializer):
    """Serializer for user data (read-only representation)."""

    full_name = serializers.ReadOnlyField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "phone",
            "avatar",
            "role",
            "is_email_verified",
            "date_joined",
        ]
        read_only_fields = ["id", "email", "role", "is_email_verified", "date_joined"]


class CustomerRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for customer registration.

    Creates a new user with CUSTOMER role and an associated CustomerProfile.
    Validates password strength and email uniqueness.
    """

    password = serializers.CharField(
        write_only=True,
        min_length=8,
        validators=[validate_password],
        style={"input_type": "password"},
    )
    password_confirm = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
    )

    class Meta:
        model = User
        fields = [
            "email",
            "first_name",
            "last_name",
            "phone",
            "password",
            "password_confirm",
        ]

    def validate_email(self, value):
        """Ensure email is unique (case-insensitive)."""
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(
                "A user with this email address already exists."
            )
        return value.lower()

    def validate(self, attrs):
        """Ensure passwords match."""
        if attrs["password"] != attrs.pop("password_confirm"):
            raise serializers.ValidationError(
                {"password_confirm": "Passwords do not match."}
            )
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        """Create user and customer profile in a single transaction."""
        user = User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
            phone=validated_data.get("phone", ""),
            role=User.Role.CUSTOMER,
        )
        CustomerProfile.objects.create(user=user)
        return user


class VendorRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for vendor registration.

    Creates a new user with VENDOR role and an associated VendorProfile.
    Requires store name and optional business details.
    """

    password = serializers.CharField(
        write_only=True,
        min_length=8,
        validators=[validate_password],
        style={"input_type": "password"},
    )
    password_confirm = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
    )
    store_name = serializers.CharField(max_length=255)
    store_description = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = User
        fields = [
            "email",
            "first_name",
            "last_name",
            "phone",
            "password",
            "password_confirm",
            "store_name",
            "store_description",
        ]

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(
                "A user with this email address already exists."
            )
        return value.lower()

    def validate_store_name(self, value):
        """Ensure store name is unique."""
        if VendorProfile.objects.filter(store_name__iexact=value).exists():
            raise serializers.ValidationError(
                "A store with this name already exists."
            )
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs.pop("password_confirm"):
            raise serializers.ValidationError(
                {"password_confirm": "Passwords do not match."}
            )
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        store_name = validated_data.pop("store_name")
        store_description = validated_data.pop("store_description", "")

        user = User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
            phone=validated_data.get("phone", ""),
            role=User.Role.VENDOR,
        )

        # Generate unique slug from store name
        base_slug = slugify(store_name)
        slug = base_slug
        counter = 1
        while VendorProfile.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

        VendorProfile.objects.create(
            user=user,
            store_name=store_name,
            slug=slug,
            description=store_description,
        )
        return user


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user profile information."""

    class Meta:
        model = User
        fields = ["first_name", "last_name", "phone", "avatar"]

    def validate_phone(self, value):
        if value and not value.replace("+", "").replace("-", "").isdigit():
            raise serializers.ValidationError("Enter a valid phone number.")
        return value


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for changing user password."""

    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(
        required=True,
        min_length=8,
        validators=[validate_password],
    )
    new_password_confirm = serializers.CharField(required=True)

    def validate_old_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def validate(self, attrs):
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError(
                {"new_password_confirm": "New passwords do not match."}
            )
        return attrs


class VendorProfileSerializer(serializers.ModelSerializer):
    """Serializer for vendor profile data."""

    user = UserSerializer(read_only=True)
    is_approved = serializers.ReadOnlyField()

    class Meta:
        model = VendorProfile
        fields = [
            "id",
            "user",
            "store_name",
            "slug",
            "description",
            "logo",
            "banner",
            "website",
            "status",
            "is_approved",
            "total_sales",
            "total_products",
            "average_rating",
            "address_line1",
            "address_line2",
            "city",
            "state",
            "postal_code",
            "country",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "slug",
            "status",
            "total_sales",
            "total_products",
            "average_rating",
            "created_at",
        ]


class CustomerProfileSerializer(serializers.ModelSerializer):
    """Serializer for customer profile data."""

    user = UserSerializer(read_only=True)

    class Meta:
        model = CustomerProfile
        fields = [
            "id",
            "user",
            "date_of_birth",
            "gender",
            "loyalty_points",
            "total_orders",
            "total_spent",
            "newsletter_subscribed",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "loyalty_points",
            "total_orders",
            "total_spent",
            "created_at",
        ]


class AddressSerializer(serializers.ModelSerializer):
    """Serializer for customer addresses."""

    class Meta:
        model = Address
        fields = [
            "id",
            "label",
            "address_type",
            "full_name",
            "phone",
            "address_line1",
            "address_line2",
            "city",
            "state",
            "postal_code",
            "country",
            "is_default",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)


class VendorListSerializer(serializers.ModelSerializer):
    """Simplified serializer for listing vendors publicly."""

    owner_name = serializers.CharField(source="user.full_name", read_only=True)

    class Meta:
        model = VendorProfile
        fields = [
            "id",
            "store_name",
            "slug",
            "description",
            "logo",
            "owner_name",
            "total_products",
            "average_rating",
        ]
