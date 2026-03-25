"""
Request logging middleware for MegaStore.

Logs all incoming API requests with timing, status codes, and user
information for monitoring and debugging purposes.
"""

import logging
import time
import uuid

from django.conf import settings

logger = logging.getLogger("apps.middleware")


class RequestLoggingMiddleware:
    """
    Middleware that logs every HTTP request with performance metrics.

    Logs the HTTP method, path, status code, response time, user,
    and a unique request ID for each request. Skips logging for
    static files and health check endpoints to reduce noise.

    The request ID is added as a response header (X-Request-ID) and
    can be used for distributed tracing.
    """

    SKIP_PATHS = [
        "/static/",
        "/media/",
        "/api/health/",
        "/__debug__/",
        "/favicon.ico",
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip logging for static files and health checks
        if any(request.path.startswith(path) for path in self.SKIP_PATHS):
            return self.get_response(request)

        # Generate a unique request ID
        request_id = str(uuid.uuid4())[:8]
        request.request_id = request_id

        # Record start time
        start_time = time.monotonic()

        # Get user info
        user_info = self._get_user_info(request)

        # Log the incoming request
        logger.info(
            "[%s] --> %s %s %s",
            request_id,
            request.method,
            request.path,
            user_info,
        )

        # Process the request
        response = self.get_response(request)

        # Calculate response time
        duration_ms = (time.monotonic() - start_time) * 1000

        # Add request ID to response headers
        response["X-Request-ID"] = request_id

        # Log level based on status code
        status_code = response.status_code
        if status_code >= 500:
            log_fn = logger.error
        elif status_code >= 400:
            log_fn = logger.warning
        else:
            log_fn = logger.info

        log_fn(
            "[%s] <-- %s %s %d (%.1fms) %s",
            request_id,
            request.method,
            request.path,
            status_code,
            duration_ms,
            user_info,
        )

        # Log slow requests as warnings
        slow_threshold_ms = getattr(settings, "SLOW_REQUEST_THRESHOLD_MS", 2000)
        if duration_ms > slow_threshold_ms:
            logger.warning(
                "[%s] SLOW REQUEST: %s %s took %.1fms (threshold: %dms)",
                request_id,
                request.method,
                request.path,
                duration_ms,
                slow_threshold_ms,
            )

        return response

    def _get_user_info(self, request):
        """Extract user information from the request."""
        if hasattr(request, "user") and request.user.is_authenticated:
            return f"user={request.user.email}"
        return "user=anonymous"


class RequestIDMiddleware:
    """
    Simple middleware that adds a unique request ID to every request.

    Lighter alternative to RequestLoggingMiddleware when full logging
    is not needed. The request ID is available as request.request_id
    and added to the X-Request-ID response header.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.request_id = str(uuid.uuid4())[:8]
        response = self.get_response(request)
        response["X-Request-ID"] = request.request_id
        return response
