"""
Serializers for the notifications application.

Handles notification listing, detail, and bulk operations.
"""

from rest_framework import serializers

from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for notification display."""

    time_since = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            "id",
            "notification_type",
            "title",
            "message",
            "action_url",
            "related_object_id",
            "is_read",
            "read_at",
            "time_since",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "notification_type",
            "title",
            "message",
            "action_url",
            "related_object_id",
            "created_at",
        ]

    def get_time_since(self, obj):
        """Return a human-readable time since the notification was created."""
        from django.utils import timezone
        from django.utils.timesince import timesince

        now = timezone.now()
        diff = now - obj.created_at

        if diff.total_seconds() < 60:
            return "just now"
        return f"{timesince(obj.created_at, now)} ago"


class NotificationMarkReadSerializer(serializers.Serializer):
    """Serializer for marking notifications as read."""

    notification_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        help_text="List of notification IDs to mark as read. If empty, marks all as read.",
    )

    def validate_notification_ids(self, value):
        """Verify all notification IDs belong to the requesting user."""
        if not value:
            return value

        user = self.context["request"].user
        existing_ids = set(
            Notification.objects.filter(
                id__in=value,
                recipient=user,
            ).values_list("id", flat=True)
        )

        invalid_ids = set(value) - existing_ids
        if invalid_ids:
            raise serializers.ValidationError(
                f"Notification(s) not found: {', '.join(str(i) for i in invalid_ids)}"
            )

        return value
