"""
Notification models for MegaStore.

Provides an in-app notification system for order updates, promotions,
vendor alerts, and system announcements.
"""

import uuid

from django.conf import settings
from django.db import models


class Notification(models.Model):
    """
    In-app notification for a user.

    Supports various notification types such as order updates,
    review alerts, promotion announcements, and system messages.
    Each notification tracks read/unread state and links to
    a related object when applicable.
    """

    class NotificationType(models.TextChoices):
        ORDER_PLACED = "order_placed", "Order Placed"
        ORDER_SHIPPED = "order_shipped", "Order Shipped"
        ORDER_DELIVERED = "order_delivered", "Order Delivered"
        ORDER_CANCELLED = "order_cancelled", "Order Cancelled"
        PAYMENT_RECEIVED = "payment_received", "Payment Received"
        REFUND_PROCESSED = "refund_processed", "Refund Processed"
        NEW_REVIEW = "new_review", "New Review"
        LOW_STOCK = "low_stock", "Low Stock Alert"
        VENDOR_APPROVED = "vendor_approved", "Vendor Approved"
        VENDOR_PAYOUT = "vendor_payout", "Vendor Payout"
        PROMOTION = "promotion", "Promotion"
        SYSTEM = "system", "System"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    notification_type = models.CharField(
        max_length=30,
        choices=NotificationType.choices,
        db_index=True,
    )
    title = models.CharField(max_length=255)
    message = models.TextField()

    # Optional link to a related object (order, product, etc.)
    action_url = models.CharField(max_length=500, blank=True)
    related_object_id = models.UUIDField(null=True, blank=True)

    is_read = models.BooleanField(default=False, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "notification"
        verbose_name_plural = "notifications"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "is_read"]),
            models.Index(fields=["-created_at"]),
            models.Index(fields=["notification_type"]),
        ]

    def __str__(self):
        status = "read" if self.is_read else "unread"
        return f"[{status}] {self.title} -> {self.recipient.email}"

    def mark_read(self):
        """Mark this notification as read."""
        from django.utils import timezone

        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=["is_read", "read_at"])

    @classmethod
    def create_notification(cls, recipient, notification_type, title, message,
                            action_url="", related_object_id=None):
        """
        Factory method to create and return a new notification.

        Args:
            recipient: User instance to receive the notification.
            notification_type: One of NotificationType choices.
            title: Short notification title.
            message: Full notification message.
            action_url: Optional URL the user can navigate to.
            related_object_id: Optional UUID of a related object.

        Returns:
            Notification: The created notification instance.
        """
        return cls.objects.create(
            recipient=recipient,
            notification_type=notification_type,
            title=title,
            message=message,
            action_url=action_url,
            related_object_id=related_object_id,
        )

    @classmethod
    def unread_count(cls, user):
        """Return the count of unread notifications for a user."""
        return cls.objects.filter(recipient=user, is_read=False).count()

    @classmethod
    def mark_all_read(cls, user):
        """Mark all notifications for a user as read."""
        from django.utils import timezone

        cls.objects.filter(
            recipient=user,
            is_read=False,
        ).update(is_read=True, read_at=timezone.now())
