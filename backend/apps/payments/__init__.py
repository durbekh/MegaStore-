"""Payments application for Stripe integration and transaction management."""

default_app_config = "apps.payments.apps.PaymentsConfig"


class PaymentsConfig:
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.payments"
    verbose_name = "Payments & Transactions"
