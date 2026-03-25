"""Products application for catalog, categories, reviews, and search."""

default_app_config = "apps.products.apps.ProductsConfig"


class ProductsConfig:
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.products"
    verbose_name = "Products & Catalog"
