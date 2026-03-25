"""Accounts application for user management, authentication, and profiles."""

default_app_config = "apps.accounts.apps.AccountsConfig"


class AccountsConfig:
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"
    verbose_name = "Accounts & Authentication"

    def ready(self):
        import apps.accounts.signals  # noqa: F401
