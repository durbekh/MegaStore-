"""
Views for the payments application.

Handles payment intent creation, confirmation, refunds,
and Stripe webhook processing.
"""

import logging

import stripe
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.orders.models import Order
from apps.orders.tasks import send_order_confirmation_email, send_order_status_update_email

from .models import Payment
from .services import StripeService

logger = logging.getLogger(__name__)


class CreatePaymentIntentView(APIView):
    """
    Create a Stripe PaymentIntent for an order.

    Requires the order ID in the request body. Returns the
    client secret needed by the frontend to confirm payment.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        order_id = request.data.get("order_id")

        if not order_id:
            return Response(
                {"error": "order_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            order = Order.objects.get(
                id=order_id,
                customer=request.user,
                payment_status="unpaid",
            )
        except Order.DoesNotExist:
            return Response(
                {"error": "Order not found or already paid."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Check if a payment intent already exists for this order
        existing_payment = Payment.objects.filter(
            order=order,
            status__in=[Payment.Status.PENDING, Payment.Status.PROCESSING],
        ).first()

        if existing_payment:
            return Response(
                {
                    "client_secret": existing_payment.stripe_client_secret,
                    "payment_intent_id": existing_payment.stripe_payment_intent_id,
                }
            )

        try:
            payment = StripeService.create_payment_intent(order, request.user)
            return Response(
                {
                    "client_secret": payment.stripe_client_secret,
                    "payment_intent_id": payment.stripe_payment_intent_id,
                },
                status=status.HTTP_201_CREATED,
            )
        except stripe.error.StripeError as e:
            return Response(
                {"error": f"Payment processing error: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class ConfirmPaymentView(APIView):
    """
    Confirm a payment after client-side Stripe.js completion.

    This endpoint is called by the frontend after the user
    completes the Stripe Elements payment flow.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        payment_intent_id = request.data.get("payment_intent_id")

        if not payment_intent_id:
            return Response(
                {"error": "payment_intent_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            payment = StripeService.confirm_payment(payment_intent_id)

            if payment.status == Payment.Status.SUCCEEDED:
                # Send order confirmation email
                send_order_confirmation_email.delay(str(payment.order.id))

                return Response(
                    {
                        "status": "succeeded",
                        "order_number": payment.order.order_number,
                        "message": "Payment confirmed successfully.",
                    }
                )
            else:
                return Response(
                    {
                        "status": payment.status,
                        "message": "Payment was not successful.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except Payment.DoesNotExist:
            return Response(
                {"error": "Payment not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except stripe.error.StripeError as e:
            return Response(
                {"error": f"Payment confirmation error: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class RefundPaymentView(APIView):
    """
    Request a refund for a payment.

    Supports full and partial refunds.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        order_id = request.data.get("order_id")
        amount = request.data.get("amount")  # None for full refund
        reason = request.data.get("reason", "")

        if not order_id:
            return Response(
                {"error": "order_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            order = Order.objects.get(id=order_id)

            # Only the customer or admin can request a refund
            if not (request.user == order.customer or request.user.is_admin):
                return Response(
                    {"error": "You do not have permission to refund this order."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            payment = Payment.objects.get(
                order=order,
                status=Payment.Status.SUCCEEDED,
            )

            from decimal import Decimal

            refund_amount = Decimal(str(amount)) if amount else None

            payment = StripeService.process_refund(payment, refund_amount, reason)

            send_order_status_update_email.delay(str(order.id), "refunded")

            return Response(
                {
                    "status": payment.status,
                    "refund_amount": str(payment.refund_amount),
                    "message": "Refund processed successfully.",
                }
            )

        except Order.DoesNotExist:
            return Response(
                {"error": "Order not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Payment.DoesNotExist:
            return Response(
                {"error": "No completed payment found for this order."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except stripe.error.StripeError as e:
            return Response(
                {"error": f"Refund processing error: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class StripeWebhookView(APIView):
    """
    Handle Stripe webhook events.

    Processes asynchronous events from Stripe such as
    payment success/failure, refund completion, and
    Connect account updates.

    This endpoint does not require authentication as it
    is called by Stripe's servers. Instead, it verifies
    the webhook signature.
    """

    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        payload = request.body
        sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")

        try:
            event = stripe.Webhook.construct_event(
                payload,
                sig_header,
                settings.STRIPE_WEBHOOK_SECRET,
            )
        except ValueError:
            logger.error("Stripe webhook: invalid payload")
            return HttpResponse(status=400)
        except stripe.error.SignatureVerificationError:
            logger.error("Stripe webhook: invalid signature")
            return HttpResponse(status=400)

        # Handle the event
        event_type = event["type"]
        data = event["data"]["object"]

        logger.info("Stripe webhook received: %s", event_type)

        if event_type == "payment_intent.succeeded":
            self._handle_payment_succeeded(data)

        elif event_type == "payment_intent.payment_failed":
            self._handle_payment_failed(data)

        elif event_type == "charge.refunded":
            self._handle_refund(data)

        elif event_type == "account.updated":
            self._handle_account_updated(data)

        return HttpResponse(status=200)

    def _handle_payment_succeeded(self, data):
        """Handle successful payment."""
        payment_intent_id = data["id"]
        try:
            StripeService.confirm_payment(payment_intent_id)
        except Exception as e:
            logger.error("Error handling payment_intent.succeeded: %s", str(e))

    def _handle_payment_failed(self, data):
        """Handle failed payment."""
        payment_intent_id = data["id"]
        try:
            payment = Payment.objects.get(
                stripe_payment_intent_id=payment_intent_id
            )
            payment.status = Payment.Status.FAILED
            payment.failure_reason = data.get("last_payment_error", {}).get(
                "message", "Payment failed"
            )
            payment.save()
            logger.info("Payment failed: %s", payment_intent_id)
        except Payment.DoesNotExist:
            logger.warning("Payment not found for failed intent: %s", payment_intent_id)

    def _handle_refund(self, data):
        """Handle completed refund."""
        payment_intent_id = data.get("payment_intent")
        if payment_intent_id:
            try:
                payment = Payment.objects.get(
                    stripe_payment_intent_id=payment_intent_id
                )
                if data.get("refunded"):
                    payment.status = Payment.Status.REFUNDED
                    payment.refunded_at = timezone.now()
                    payment.save()
            except Payment.DoesNotExist:
                pass

    def _handle_account_updated(self, data):
        """Handle Stripe Connect account updates."""
        from apps.accounts.models import VendorProfile

        account_id = data["id"]
        try:
            vendor = VendorProfile.objects.get(stripe_account_id=account_id)

            # Check if onboarding is complete
            if data.get("charges_enabled") and data.get("payouts_enabled"):
                vendor.stripe_onboarding_complete = True
                vendor.save(update_fields=["stripe_onboarding_complete", "updated_at"])
                logger.info(
                    "Vendor %s Stripe onboarding complete", vendor.store_name
                )
        except VendorProfile.DoesNotExist:
            logger.warning("Vendor not found for Stripe account: %s", account_id)
