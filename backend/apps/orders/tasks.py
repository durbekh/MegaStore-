"""
Celery tasks for the orders application.

Handles asynchronous operations related to order processing:
confirmation emails, status updates, abandoned cart reminders,
and daily sales reports.
"""

import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    queue="emails",
)
def send_order_confirmation_email(self, order_id):
    """
    Send an order confirmation email to the customer.

    Includes order number, items summary, total, and shipping address.
    """
    try:
        from .models import Order

        order = Order.objects.select_related("customer").prefetch_related(
            "items__product"
        ).get(id=order_id)

        items_summary = "\n".join(
            f"  - {item.product_name} x{item.quantity}: ${item.total_price:.2f}"
            for item in order.items.all()
        )

        subject = f"Order Confirmation - {order.order_number}"
        message = (
            f"Hi {order.customer.first_name},\n\n"
            f"Thank you for your order! Here are the details:\n\n"
            f"Order Number: {order.order_number}\n"
            f"Date: {order.created_at.strftime('%B %d, %Y')}\n\n"
            f"Items:\n{items_summary}\n\n"
            f"Subtotal: ${order.subtotal:.2f}\n"
            f"Shipping: ${order.shipping_cost:.2f}\n"
            f"Tax: ${order.tax_amount:.2f}\n"
            f"Total: ${order.total_amount:.2f}\n\n"
            f"Shipping to:\n"
            f"  {order.shipping_full_name}\n"
            f"  {order.shipping_address_line1}\n"
        )

        if order.shipping_address_line2:
            message += f"  {order.shipping_address_line2}\n"

        message += (
            f"  {order.shipping_city}, {order.shipping_state} {order.shipping_postal_code}\n"
            f"  {order.shipping_country}\n\n"
            f"We'll notify you when your order ships.\n\n"
            f"Best regards,\n"
            f"The {settings.PLATFORM_NAME} Team"
        )

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.customer.email],
            fail_silently=False,
        )

        logger.info("Order confirmation email sent for order %s", order.order_number)

    except Exception as exc:
        logger.error("Failed to send order confirmation email for %s: %s", order_id, exc)
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    queue="emails",
)
def send_order_status_update_email(self, order_id, new_status):
    """Send an email when order status changes."""
    try:
        from .models import Order

        order = Order.objects.select_related("customer").get(id=order_id)

        status_messages = {
            "confirmed": "Your payment has been confirmed and your order is being processed.",
            "processing": "Your order is being prepared by our vendors.",
            "shipped": (
                f"Your order has been shipped!\n\n"
                f"Tracking Number: {order.tracking_number or 'N/A'}\n"
                + (f"Track here: {order.tracking_url}\n" if order.tracking_url else "")
            ),
            "delivered": "Your order has been delivered. We hope you enjoy your purchase!",
            "cancelled": "Your order has been cancelled. If you paid, a refund will be processed.",
            "refunded": "Your refund has been processed. It may take 5-10 business days to appear.",
        }

        status_text = status_messages.get(new_status, f"Your order status has been updated to: {new_status}")

        subject = f"Order {order.order_number} - Status Update"
        message = (
            f"Hi {order.customer.first_name},\n\n"
            f"Your order {order.order_number} has been updated.\n\n"
            f"{status_text}\n\n"
            f"Best regards,\n"
            f"The {settings.PLATFORM_NAME} Team"
        )

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.customer.email],
            fail_silently=False,
        )

        logger.info(
            "Order status update email sent for order %s (status: %s)",
            order.order_number,
            new_status,
        )

    except Exception as exc:
        logger.error(
            "Failed to send status update email for order %s: %s", order_id, exc
        )
        raise self.retry(exc=exc)


@shared_task(queue="emails")
def send_abandoned_cart_reminders():
    """
    Send reminder emails to users with abandoned carts.

    Targets carts that have been inactive for 24-48 hours
    with items still in them.
    """
    from apps.cart.models import Cart

    cutoff_start = timezone.now() - timedelta(hours=48)
    cutoff_end = timezone.now() - timedelta(hours=24)

    abandoned_carts = Cart.objects.filter(
        updated_at__gte=cutoff_start,
        updated_at__lte=cutoff_end,
        items__isnull=False,
    ).distinct().select_related("user")

    sent_count = 0
    for cart in abandoned_carts:
        items = cart.items.select_related("product").all()
        if not items.exists():
            continue

        items_list = "\n".join(
            f"  - {item.product.name}: ${item.product.price:.2f}"
            for item in items[:5]
        )

        remaining = items.count() - 5
        if remaining > 0:
            items_list += f"\n  ...and {remaining} more item(s)"

        subject = f"You left items in your {settings.PLATFORM_NAME} cart!"
        message = (
            f"Hi {cart.user.first_name},\n\n"
            f"You have items waiting in your shopping cart:\n\n"
            f"{items_list}\n\n"
            f"Don't miss out - complete your purchase today!\n\n"
            f"Best regards,\n"
            f"The {settings.PLATFORM_NAME} Team"
        )

        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[cart.user.email],
                fail_silently=False,
            )
            sent_count += 1
        except Exception as exc:
            logger.error(
                "Failed to send abandoned cart reminder to %s: %s",
                cart.user.email,
                exc,
            )

    logger.info("Sent %d abandoned cart reminder emails", sent_count)
    return sent_count


@shared_task(queue="default")
def generate_daily_sales_report():
    """
    Generate and email a daily sales report to vendors.

    Summarizes yesterday's orders, revenue, and top-selling products
    for each vendor.
    """
    from django.db.models import Count, Sum

    from apps.accounts.models import VendorProfile
    from .models import OrderItem

    yesterday = timezone.now().date() - timedelta(days=1)

    vendors = VendorProfile.objects.filter(status=VendorProfile.Status.APPROVED)

    for vendor in vendors:
        vendor_items = OrderItem.objects.filter(
            vendor=vendor,
            order__payment_status="paid",
            order__created_at__date=yesterday,
        )

        if not vendor_items.exists():
            continue

        stats = vendor_items.aggregate(
            total_revenue=Sum("unit_price"),
            total_items=Sum("quantity"),
            total_orders=Count("order", distinct=True),
        )

        subject = f"{settings.PLATFORM_NAME} - Daily Sales Report ({yesterday})"
        message = (
            f"Hi {vendor.user.first_name},\n\n"
            f"Here is your sales summary for {yesterday.strftime('%B %d, %Y')}:\n\n"
            f"Orders: {stats['total_orders']}\n"
            f"Items Sold: {stats['total_items']}\n"
            f"Revenue: ${stats['total_revenue']:.2f}\n\n"
            f"Log in to your dashboard for detailed analytics.\n\n"
            f"Best regards,\n"
            f"The {settings.PLATFORM_NAME} Team"
        )

        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[vendor.user.email],
                fail_silently=False,
            )
        except Exception as exc:
            logger.error(
                "Failed to send daily report to vendor %s: %s",
                vendor.store_name,
                exc,
            )

    logger.info("Daily sales reports generated for %s", yesterday)
