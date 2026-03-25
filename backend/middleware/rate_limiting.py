"""
Custom rate limiting middleware for MegaStore.

Provides endpoint-level rate limiting beyond DRF's built-in
throttling, using Redis as the backend for distributed rate limiting.
"""

import hashlib
import logging
import time

from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse

logger = logging.getLogger("apps.middleware")


class RateLimitMiddleware:
    """
    Middleware that enforces rate limits on specific API endpoints.

    Uses a sliding window algorithm stored in Redis/cache to track
    request counts per IP or authenticated user. Returns HTTP 429
    when the rate limit is exceeded.

    Rate limits are configurable via RATE_LIMIT_CONFIG in settings:

        RATE_LIMIT_CONFIG = {
            "/api/auth/login/": {"rate": "10/minute", "scope": "ip"},
            "/api/auth/register/": {"rate": "5/hour", "scope": "ip"},
            "/api/payments/": {"rate": "30/minute", "scope": "user"},
        }
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.config = getattr(settings, "RATE_LIMIT_CONFIG", {})

    def __call__(self, request):
        # Check if the path matches any rate limit configuration
        limit_config = self._get_limit_config(request.path)

        if limit_config:
            rate = limit_config.get("rate", "100/minute")
            scope = limit_config.get("scope", "ip")

            identifier = self._get_identifier(request, scope)
            max_requests, window_seconds = self._parse_rate(rate)

            cache_key = self._build_cache_key(request.path, identifier)

            if not self._check_rate_limit(cache_key, max_requests, window_seconds):
                logger.warning(
                    "Rate limit exceeded: %s by %s on %s",
                    rate,
                    identifier,
                    request.path,
                )
                return JsonResponse(
                    {
                        "error": {
                            "code": "rate_limit_exceeded",
                            "message": "Too many requests. Please try again later.",
                            "retry_after": window_seconds,
                        }
                    },
                    status=429,
                    headers={
                        "Retry-After": str(window_seconds),
                        "X-RateLimit-Limit": str(max_requests),
                    },
                )

        response = self.get_response(request)

        # Add rate limit headers to response
        if limit_config:
            remaining = self._get_remaining(cache_key, max_requests)
            response["X-RateLimit-Limit"] = str(max_requests)
            response["X-RateLimit-Remaining"] = str(max(0, remaining))

        return response

    def _get_limit_config(self, path):
        """Find the matching rate limit config for the given path."""
        for pattern, config in self.config.items():
            if path.startswith(pattern):
                return config
        return None

    def _get_identifier(self, request, scope):
        """
        Get the rate limit identifier based on the scope.

        For 'user' scope: uses the authenticated user's ID.
        For 'ip' scope: uses the client's IP address.
        """
        if scope == "user" and hasattr(request, "user") and request.user.is_authenticated:
            return f"user:{request.user.id}"

        # Get client IP, checking for proxy headers
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0].strip()
        else:
            ip = request.META.get("REMOTE_ADDR", "unknown")

        return f"ip:{ip}"

    def _parse_rate(self, rate_string):
        """
        Parse a rate string like '10/minute' into (max_requests, window_seconds).

        Supports: second, minute, hour, day.
        """
        count, period = rate_string.split("/")
        max_requests = int(count)

        period_seconds = {
            "second": 1,
            "minute": 60,
            "hour": 3600,
            "day": 86400,
        }
        window_seconds = period_seconds.get(period.lower(), 60)

        return max_requests, window_seconds

    def _build_cache_key(self, path, identifier):
        """Build a unique cache key for the rate limit."""
        path_hash = hashlib.md5(path.encode()).hexdigest()[:8]
        return f"ratelimit:{path_hash}:{identifier}"

    def _check_rate_limit(self, cache_key, max_requests, window_seconds):
        """
        Check if the rate limit has been exceeded using a simple counter.

        Returns True if the request is allowed, False if rate limited.
        """
        current_count = cache.get(cache_key, 0)

        if current_count >= max_requests:
            return False

        # Increment the counter
        if current_count == 0:
            cache.set(cache_key, 1, timeout=window_seconds)
        else:
            cache.incr(cache_key)

        return True

    def _get_remaining(self, cache_key, max_requests):
        """Get the number of remaining requests in the current window."""
        current_count = cache.get(cache_key, 0)
        return max_requests - current_count
