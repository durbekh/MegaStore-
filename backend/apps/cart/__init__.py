"""Shopping cart application for MegaStore."""

default_app_config = "apps.cart.apps.CartConfig"


class CartConfig:
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.cart"
    verbose_name = "Shopping Cart"
