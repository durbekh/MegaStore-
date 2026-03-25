"""
Custom exception handling for MegaStore API.

Provides a unified error response format across all API endpoints
and handles both DRF and Django exceptions consistently.
"""

import logging

from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import (
    APIException,
    AuthenticationFailed,
    MethodNotAllowed,
    NotAuthenticated,
    NotFound,
    Throttled,
)
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Custom exception handler that wraps all errors in a consistent format.

    Response format:
    {
        "error": {
            "code": "error_code",
            "message": "Human-readable error message.",
            "details": {...}  // optional, field-level errors for validation
        }
    }
    """
    # Call DRF's default exception handler first to get the standard response
    response = exception_handler(exc, context)

    if response is not None:
        error_data = _format_drf_error(exc, response)
        response.data = {"error": error_data}
        return response

    # Handle exceptions not covered by DRF
    if isinstance(exc, ValidationError):
        error_data = {
            "code": "validation_error",
            "message": "Invalid input data.",
            "details": exc.message_dict if hasattr(exc, "message_dict") else {"non_field_errors": exc.messages},
        }
        return Response({"error": error_data}, status=status.HTTP_400_BAD_REQUEST)

    if isinstance(exc, Http404):
        error_data = {
            "code": "not_found",
            "message": "The requested resource was not found.",
        }
        return Response({"error": error_data}, status=status.HTTP_404_NOT_FOUND)

    if isinstance(exc, PermissionDenied):
        error_data = {
            "code": "permission_denied",
            "message": "You do not have permission to perform this action.",
        }
        return Response({"error": error_data}, status=status.HTTP_403_FORBIDDEN)

    # Unhandled exceptions - log and return a generic 500 error
    view = context.get("view", None)
    view_name = view.__class__.__name__ if view else "Unknown"
    logger.error(
        "Unhandled exception in %s: %s",
        view_name,
        str(exc),
        exc_info=True,
        extra={"request": context.get("request")},
    )

    error_data = {
        "code": "server_error",
        "message": "An unexpected error occurred. Please try again later.",
    }
    return Response({"error": error_data}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def _format_drf_error(exc, response):
    """Format a DRF exception into the standardized error structure."""
    error_code_map = {
        AuthenticationFailed: "authentication_failed",
        NotAuthenticated: "not_authenticated",
        NotFound: "not_found",
        MethodNotAllowed: "method_not_allowed",
        Throttled: "rate_limit_exceeded",
    }

    code = error_code_map.get(type(exc), "validation_error")

    if isinstance(exc, Throttled):
        message = f"Request rate limit exceeded. Try again in {exc.wait} seconds."
        return {"code": code, "message": message, "retry_after": exc.wait}

    # Handle field-level validation errors (dict of field -> errors)
    if isinstance(response.data, dict):
        # Check if it looks like field-level errors
        has_field_errors = any(
            isinstance(v, (list, dict)) for v in response.data.values()
        )
        if has_field_errors and code == "validation_error":
            return {
                "code": code,
                "message": "Invalid input data. Please check the details below.",
                "details": response.data,
            }
        # Single error message in 'detail' key
        if "detail" in response.data:
            return {
                "code": code,
                "message": str(response.data["detail"]),
            }

    # Handle list errors
    if isinstance(response.data, list):
        return {
            "code": code,
            "message": str(response.data[0]) if response.data else "An error occurred.",
            "details": response.data,
        }

    return {
        "code": code,
        "message": str(exc.detail) if hasattr(exc, "detail") else "An error occurred.",
    }


class ServiceUnavailable(APIException):
    """Raised when an external service (Stripe, email, etc.) is unavailable."""

    status_code = 503
    default_detail = "Service temporarily unavailable. Please try again later."
    default_code = "service_unavailable"


class PaymentError(APIException):
    """Raised when a payment processing error occurs."""

    status_code = 402
    default_detail = "Payment processing failed."
    default_code = "payment_error"


class InsufficientStockError(APIException):
    """Raised when requested quantity exceeds available stock."""

    status_code = 409
    default_detail = "Insufficient stock for the requested quantity."
    default_code = "insufficient_stock"
