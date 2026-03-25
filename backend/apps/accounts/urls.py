"""URL patterns for the accounts application."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from . import views

router = DefaultRouter()
router.register(r"addresses", views.AddressViewSet, basename="address")

app_name = "accounts"

urlpatterns = [
    # Authentication
    path("login/", views.CustomTokenObtainPairView.as_view(), name="login"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    # Registration
    path(
        "register/",
        views.CustomerRegistrationView.as_view(),
        name="customer-register",
    ),
    path(
        "register/vendor/",
        views.VendorRegistrationView.as_view(),
        name="vendor-register",
    ),
    # Profile Management
    path("profile/", views.UserProfileView.as_view(), name="user-profile"),
    path(
        "profile/change-password/",
        views.ChangePasswordView.as_view(),
        name="change-password",
    ),
    path(
        "profile/vendor/",
        views.VendorProfileUpdateView.as_view(),
        name="vendor-profile",
    ),
    path(
        "profile/customer/",
        views.CustomerProfileUpdateView.as_view(),
        name="customer-profile",
    ),
    # Addresses (ViewSet routes)
    path("", include(router.urls)),
    # Public vendor endpoints
    path("vendors/", views.VendorListView.as_view(), name="vendor-list"),
    path(
        "vendors/<slug:slug>/",
        views.VendorDetailView.as_view(),
        name="vendor-detail",
    ),
    # Admin endpoints
    path(
        "admin/vendors/<uuid:vendor_id>/approval/",
        views.AdminVendorApprovalView.as_view(),
        name="vendor-approval",
    ),
]
