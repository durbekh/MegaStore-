"""
Custom permissions for the accounts application.

Provides role-based access control for vendor, customer, and admin roles.
"""

from rest_framework.permissions import BasePermission


class IsVendor(BasePermission):
    """Allow access only to users with the VENDOR role."""

    message = "Only vendors can perform this action."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.is_vendor
        )


class IsApprovedVendor(BasePermission):
    """Allow access only to vendors with an approved profile."""

    message = "Your vendor account must be approved to perform this action."

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated and request.user.is_vendor):
            return False
        try:
            return request.user.vendor_profile.is_approved
        except Exception:
            return False


class IsCustomer(BasePermission):
    """Allow access only to users with the CUSTOMER role."""

    message = "Only customers can perform this action."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.is_customer
        )


class IsAdminUser(BasePermission):
    """Allow access only to users with the ADMIN role or superuser status."""

    message = "Only administrators can perform this action."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and (request.user.is_admin or request.user.is_superuser)
        )


class IsAccountOwner(BasePermission):
    """Allow access only to the owner of the account/resource."""

    message = "You can only access your own resources."

    def has_object_permission(self, request, view, obj):
        if hasattr(obj, "user"):
            return obj.user == request.user
        return obj == request.user


class IsVendorOrAdmin(BasePermission):
    """Allow access to vendors and admins."""

    message = "Only vendors and administrators can perform this action."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and (request.user.is_vendor or request.user.is_admin or request.user.is_superuser)
        )


class IsProductOwnerOrAdmin(BasePermission):
    """
    Object-level permission to allow only the product's vendor
    or an admin to modify it.
    """

    message = "You do not have permission to modify this product."

    def has_object_permission(self, request, view, obj):
        if request.user.is_admin or request.user.is_superuser:
            return True
        if hasattr(obj, "vendor"):
            return obj.vendor.user == request.user
        return False
