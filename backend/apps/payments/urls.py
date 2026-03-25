"""URL patterns for the payments application."""

from django.urls import path

from . import views

app_name = "payments"

urlpatterns = [
    path(
        "create-intent/",
        views.CreatePaymentIntentView.as_view(),
        name="create-payment-intent",
    ),
    path(
        "confirm/",
        views.ConfirmPaymentView.as_view(),
        name="confirm-payment",
    ),
    path(
        "refund/",
        views.RefundPaymentView.as_view(),
        name="refund-payment",
    ),
    path(
        "webhook/stripe/",
        views.StripeWebhookView.as_view(),
        name="stripe-webhook",
    ),
]
