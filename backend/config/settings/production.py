"""
Production settings for MegaStore.

Extends base settings with production-specific hardening and optimization.
These settings should be used when deploying to production environments.
"""

import sentry_sdk
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.redis import RedisIntegration

from .base import *  # noqa: F401, F403

# =============================================================================
# Debug Mode (MUST be False in production)
# =============================================================================

DEBUG = False

ALLOWED_HOSTS = config(  # noqa: F405
    "ALLOWED_HOSTS", cast=Csv()  # noqa: F405
)

# =============================================================================
# Security Settings
# =============================================================================

SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=True, cast=bool)  # noqa: F405
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True

SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"

CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_TRUSTED_ORIGINS = config(  # noqa: F405
    "CSRF_TRUSTED_ORIGINS",
    default="",
    cast=Csv(),  # noqa: F405
)

X_FRAME_OPTIONS = "DENY"

# =============================================================================
# Database Connection Pooling
# =============================================================================

DATABASES["default"]["CONN_MAX_AGE"] = 600  # noqa: F405
DATABASES["default"]["OPTIONS"] = {  # noqa: F405
    "connect_timeout": 10,
    "options": "-c default_transaction_isolation=read\\ committed",
}

# =============================================================================
# Caching (Production Redis)
# =============================================================================

CACHES["default"]["OPTIONS"]["CONNECTION_POOL_KWARGS"] = {  # noqa: F405
    "max_connections": 100,
}
CACHES["default"]["TIMEOUT"] = 600  # noqa: F405

# =============================================================================
# Static Files (Compressed & Hashed)
# =============================================================================

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# =============================================================================
# Media Files (S3 in production)
# =============================================================================

AWS_ACCESS_KEY_ID = config("AWS_ACCESS_KEY_ID", default="")  # noqa: F405
AWS_SECRET_ACCESS_KEY = config("AWS_SECRET_ACCESS_KEY", default="")  # noqa: F405
AWS_STORAGE_BUCKET_NAME = config("AWS_STORAGE_BUCKET_NAME", default="")  # noqa: F405
AWS_S3_REGION_NAME = config("AWS_S3_REGION_NAME", default="us-east-1")  # noqa: F405

if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY and AWS_STORAGE_BUCKET_NAME:
    DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
    AWS_S3_CUSTOM_DOMAIN = (
        f"{AWS_STORAGE_BUCKET_NAME}.s3.{AWS_S3_REGION_NAME}.amazonaws.com"
    )
    AWS_DEFAULT_ACL = "public-read"
    AWS_S3_OBJECT_PARAMETERS = {
        "CacheControl": "max-age=86400",
    }
    AWS_QUERYSTRING_AUTH = False
    MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/media/"

# =============================================================================
# Email (SMTP in production)
# =============================================================================

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

# =============================================================================
# Logging (Production-grade)
# =============================================================================

LOGGING["handlers"]["file"]["level"] = "WARNING"  # noqa: F405
LOGGING["loggers"]["django"]["level"] = "WARNING"  # noqa: F405
LOGGING["loggers"]["apps"]["level"] = "INFO"  # noqa: F405

# =============================================================================
# Sentry Error Tracking
# =============================================================================

SENTRY_DSN = config("SENTRY_DSN", default="")  # noqa: F405

if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            DjangoIntegration(),
            CeleryIntegration(),
            RedisIntegration(),
        ],
        traces_sample_rate=config(  # noqa: F405
            "SENTRY_TRACES_SAMPLE_RATE", default=0.1, cast=float  # noqa: F405
        ),
        send_default_pii=False,
        environment="production",
        release=config("APP_VERSION", default="1.0.0"),  # noqa: F405
    )

# =============================================================================
# API Throttling (Stricter in production)
# =============================================================================

REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {  # noqa: F405
    "anon": "50/hour",
    "user": "500/hour",
}
