"""URL patterns for the coupons application."""

from django.urls import path

from . import views

app_name = "coupons"

urlpatterns = [
    path("", views.CouponListView.as_view(), name="coupon-list"),
    path("create/", views.CouponCreateView.as_view(), name="coupon-create"),
    path("validate/", views.ValidateCouponView.as_view(), name="coupon-validate"),
    path("<uuid:pk>/", views.CouponDetailView.as_view(), name="coupon-detail"),
]
