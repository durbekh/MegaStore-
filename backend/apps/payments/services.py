"""
Stripe payment service for MegaStore.

Provides a centralized service layer for all Stripe operations:
- Creating payment intents
- Confirming payments
- Processing refunds
- Managing vendor Connect accounts
- Handling vendor payouts
"""

import logging
from decimal import Decimal

import stripe
from django.conf import settings
from django.utils import timezone

from .models import Payment, VendorPayout

logger = logging.getLogger(__name__)

# Configure Stripe API key
stripe.api_key = settings.STRIPE_SECRET_KEY


class StripeService:
    """
    Service class encapsulating all Stripe API interactions.

    All methods are designed to be idempotent where possible
    and handle errors gracefully with proper logging.
    """

    @staticmethod
    def create_payment_intent(order, user):
        """
        Create a Stripe PaymentIntent for an order.

        Returns a Payment model instance with the client secret
        needed by the frontend to confirm the payment.

        Args:
            order: The Order instance to create payment for.
            user: The authenticated user making the payment.

        Returns:
            Payment: The created Payment model instance.

        Raises:
            stripe.error.StripeError: If Stripe API call fails.
        """
        amount_cents = int(order.total_amount * 100)

        try:
            # Create Stripe PaymentIntent
            intent = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency="usd",
                metadata={
                    "order_id": str(order.id),
                    "order_number": order.order_number,
                    "customer_email": user.email,
                },
                receipt_email=user.email,
                automatic_payment_methods={"enabled": True},
            )

            # Calculate platform fee
            platform_fee = order.total_amount * (
                Decimal(str(settings.STRIPE_PLATFORM_FEE_PERCENT)) / Decimal("100")
            )

            # Create Payment record
            payment = Payment.objects.create(
                order=order,
                user=user,
                stripe_payment_intent_id=intent.id,
                stripe_client_secret=intent.client_secret,
                amount=order.total_amount,
                platform_fee=platform_fee,
                status=Payment.Status.PENDING,
            )

            logger.info(
                "PaymentIntent created: %s for order %s ($%s)",
                intent.id,
                order.order_number,
                order.total_amount,
            )

            return payment

        except stripe.error.StripeError as e:
            logger.error(
                "Stripe error creating PaymentIntent for order %s: %s",
                order.order_number,
                str(e),
            )
            raise

    @staticmethod
    def confirm_payment(payment_intent_id):
        """
        Confirm a payment after Stripe webhook notification.

        Updates the Payment record and marks the associated order as confirmed.

        Args:
            payment_intent_id: The Stripe PaymentIntent ID.

        Returns:
            Payment: The updated Payment instance.
        """
        try:
            payment = Payment.objects.select_related("order").get(
                stripe_payment_intent_id=payment_intent_id
            )

            # Retrieve the latest state from Stripe
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)

            if intent.status == "succeeded":
                payment.status = Payment.Status.SUCCEEDED
                payment.stripe_charge_id = (
                    intent.latest_charge if intent.latest_charge else ""
                )

                # Extract card details if available
                if intent.charges and intent.charges.data:
                    charge = intent.charges.data[0]
                    if charge.payment_method_details:
                        card = getattr(charge.payment_method_details, "card", None)
                        if card:
                            payment.card_last4 = card.last4 or ""
                            payment.card_brand = card.brand or ""
                        payment.payment_method_type = (
                            charge.payment_method_details.type or ""
                        )

                payment.save()

                # Confirm the order
                payment.order.confirm_payment(payment_intent_id)

                logger.info(
                    "Payment confirmed: %s for order %s",
                    payment_intent_id,
                    payment.order.order_number,
                )

            elif intent.status == "canceled":
                payment.status = Payment.Status.CANCELLED
                payment.save()

            return payment

        except Payment.DoesNotExist:
            logger.error("Payment not found for intent: %s", payment_intent_id)
            raise
        except stripe.error.StripeError as e:
            logger.error("Stripe error confirming payment %s: %s", payment_intent_id, str(e))
            raise

    @staticmethod
    def process_refund(payment, amount=None, reason=""):
        """
        Process a refund for a payment.

        Supports full and partial refunds.

        Args:
            payment: The Payment instance to refund.
            amount: Amount to refund (None for full refund).
            reason: Reason for the refund.

        Returns:
            Payment: The updated Payment instance.
        """
        try:
            refund_amount = amount or payment.amount
            refund_amount_cents = int(refund_amount * 100)

            refund = stripe.Refund.create(
                payment_intent=payment.stripe_payment_intent_id,
                amount=refund_amount_cents,
                reason="requested_by_customer",
                metadata={"reason": reason},
            )

            payment.refund_amount += refund_amount
            payment.refund_reason = reason
            payment.refunded_at = timezone.now()

            if payment.refund_amount >= payment.amount:
                payment.status = Payment.Status.REFUNDED
            else:
                payment.status = Payment.Status.PARTIALLY_REFUNDED

            payment.save()

            # Update order status
            if payment.refund_amount >= payment.amount:
                payment.order.status = "refunded"
                payment.order.save(update_fields=["status", "updated_at"])

            logger.info(
                "Refund processed: $%s for payment %s (order %s)",
                refund_amount,
                payment.stripe_payment_intent_id,
                payment.order.order_number,
            )

            return payment

        except stripe.error.StripeError as e:
            logger.error(
                "Stripe error processing refund for %s: %s",
                payment.stripe_payment_intent_id,
                str(e),
            )
            raise

    @staticmethod
    def create_vendor_connect_account(vendor):
        """
        Create a Stripe Connect account for a vendor.

        This sets up the vendor to receive payouts for their sales.

        Args:
            vendor: The VendorProfile instance.

        Returns:
            dict: Contains the account ID and onboarding URL.
        """
        try:
            account = stripe.Account.create(
                type="express",
                country=vendor.country or "US",
                email=vendor.user.email,
                capabilities={
                    "card_payments": {"requested": True},
                    "transfers": {"requested": True},
                },
                business_profile={
                    "name": vendor.store_name,
                    "url": vendor.website or None,
                },
                metadata={
                    "vendor_id": str(vendor.id),
                    "store_name": vendor.store_name,
                },
            )

            vendor.stripe_account_id = account.id
            vendor.save(update_fields=["stripe_account_id", "updated_at"])

            # Create onboarding link
            account_link = stripe.AccountLink.create(
                account=account.id,
                refresh_url=f"{settings.CORS_ALLOWED_ORIGINS[0]}/vendor/stripe/refresh",
                return_url=f"{settings.CORS_ALLOWED_ORIGINS[0]}/vendor/stripe/complete",
                type="account_onboarding",
            )

            logger.info(
                "Stripe Connect account created for vendor %s: %s",
                vendor.store_name,
                account.id,
            )

            return {
                "account_id": account.id,
                "onboarding_url": account_link.url,
            }

        except stripe.error.StripeError as e:
            logger.error(
                "Stripe error creating Connect account for %s: %s",
                vendor.store_name,
                str(e),
            )
            raise

    @staticmethod
    def create_vendor_payout(vendor, order, amount):
        """
        Create a transfer to a vendor's Stripe Connect account.

        Deducts the platform fee and transfers the remaining amount.

        Args:
            vendor: The VendorProfile instance.
            order: The Order instance.
            amount: The gross amount before platform fee.

        Returns:
            VendorPayout: The created payout record.
        """
        if not vendor.stripe_account_id:
            logger.warning(
                "Cannot create payout for vendor %s: no Stripe account",
                vendor.store_name,
            )
            return None

        try:
            platform_fee = amount * (
                Decimal(str(settings.STRIPE_PLATFORM_FEE_PERCENT)) / Decimal("100")
            )
            net_amount = amount - platform_fee
            transfer_amount_cents = int(net_amount * 100)

            transfer = stripe.Transfer.create(
                amount=transfer_amount_cents,
                currency="usd",
                destination=vendor.stripe_account_id,
                metadata={
                    "order_id": str(order.id),
                    "order_number": order.order_number,
                    "vendor_id": str(vendor.id),
                },
            )

            payout = VendorPayout.objects.create(
                vendor=vendor,
                order=order,
                gross_amount=amount,
                platform_fee=platform_fee,
                net_amount=net_amount,
                stripe_transfer_id=transfer.id,
                status=VendorPayout.Status.PROCESSING,
            )

            logger.info(
                "Vendor payout created: $%s to %s for order %s",
                net_amount,
                vendor.store_name,
                order.order_number,
            )

            return payout

        except stripe.error.StripeError as e:
            logger.error(
                "Stripe error creating payout for vendor %s: %s",
                vendor.store_name,
                str(e),
            )
            # Create a failed payout record
            VendorPayout.objects.create(
                vendor=vendor,
                order=order,
                gross_amount=amount,
                platform_fee=Decimal("0"),
                net_amount=Decimal("0"),
                status=VendorPayout.Status.FAILED,
                failure_reason=str(e),
            )
            raise
