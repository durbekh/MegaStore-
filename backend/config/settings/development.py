"""
Development settings for MegaStore.

Extends base settings with development-specific configuration.
Do NOT use these settings in production.
"""

from .base import *  # noqa: F401, F403

# =============================================================================
# Debug Mode
# =============================================================================

DEBUG = True

ALLOWED_HOSTS = ["*"]

# =============================================================================
# Additional Development Apps
# =============================================================================

INSTALLED_APPS += [  # noqa: F405
    "debug_toolbar",
]

# =============================================================================
# Additional Middleware
# =============================================================================

MIDDLEWARE.insert(  # noqa: F405
    MIDDLEWARE.index("django.middleware.common.CommonMiddleware"),  # noqa: F405
    "debug_toolbar.middleware.DebugToolbarMiddleware",
)

# =============================================================================
# Debug Toolbar Configuration
# =============================================================================

INTERNAL_IPS = ["127.0.0.1", "localhost", "0.0.0.0"]

DEBUG_TOOLBAR_CONFIG = {
    "SHOW_TOOLBAR_CALLBACK": lambda request: DEBUG,
    "INTERCEPT_REDIRECTS": False,
}

# =============================================================================
# Email Backend (Console in development)
# =============================================================================

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# =============================================================================
# CORS (Allow all in development)
# =============================================================================

CORS_ALLOW_ALL_ORIGINS = True

# =============================================================================
# DRF (Add browsable API renderer in development)
# =============================================================================

REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = [  # noqa: F405
    "rest_framework.renderers.JSONRenderer",
    "rest_framework.renderers.BrowsableAPIRenderer",
]

# Disable throttling in development
REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] = []  # noqa: F405
REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {}  # noqa: F405

# =============================================================================
# Caching (Use local memory cache in development if Redis is unavailable)
# =============================================================================

# Uncomment below to use local memory cache instead of Redis:
# CACHES = {
#     "default": {
#         "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
#         "LOCATION": "megastore-dev-cache",
#     }
# }

# =============================================================================
# Logging (More verbose in development)
# =============================================================================

LOGGING["loggers"]["apps"]["level"] = "DEBUG"  # noqa: F405
LOGGING["loggers"]["django"]["level"] = "DEBUG"  # noqa: F405

# =============================================================================
# Static Files (No compression in development)
# =============================================================================

STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"

# =============================================================================
# Security (Relaxed in development)
# =============================================================================

CSRF_TRUSTED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]
