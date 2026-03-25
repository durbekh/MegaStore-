"""
Views for the notifications application.

Handles listing, reading, and managing in-app notifications.
"""

import logging

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Notification
from .serializers import NotificationMarkReadSerializer, NotificationSerializer

logger = logging.getLogger(__name__)


class NotificationListView(generics.ListAPIView):
    """
    List notifications for the authenticated user.

    Returns paginated notifications sorted by most recent first.
    Supports filtering by read/unread status and notification type.
    """

    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = Notification.objects.filter(recipient=self.request.user)

        # Filter by read status
        is_read = self.request.query_params.get("is_read")
        if is_read is not None:
            queryset = queryset.filter(is_read=is_read.lower() == "true")

        # Filter by notification type
        notification_type = self.request.query_params.get("type")
        if notification_type:
            queryset = queryset.filter(notification_type=notification_type)

        return queryset


class NotificationDetailView(generics.RetrieveAPIView):
    """
    Retrieve a single notification and mark it as read.

    Automatically marks the notification as read when accessed.
    """

    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.mark_read()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class NotificationMarkReadView(APIView):
    """
    Mark notifications as read.

    POST with notification_ids to mark specific notifications as read,
    or POST with an empty body to mark all notifications as read.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = NotificationMarkReadSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        notification_ids = serializer.validated_data.get("notification_ids", [])

        if notification_ids:
            # Mark specific notifications as read
            from django.utils import timezone

            updated = Notification.objects.filter(
                id__in=notification_ids,
                recipient=request.user,
                is_read=False,
            ).update(is_read=True, read_at=timezone.now())
            message = f"{updated} notification(s) marked as read."
        else:
            # Mark all notifications as read
            Notification.mark_all_read(request.user)
            message = "All notifications marked as read."

        logger.info("User %s marked notifications as read", request.user.email)

        return Response({"message": message}, status=status.HTTP_200_OK)


class NotificationCountView(APIView):
    """
    Get the unread notification count for the authenticated user.

    Lightweight endpoint for displaying badge counts in the UI.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        unread_count = Notification.unread_count(request.user)
        return Response({"unread_count": unread_count})


class NotificationDeleteView(APIView):
    """Delete a specific notification."""

    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, pk):
        try:
            notification = Notification.objects.get(
                id=pk,
                recipient=request.user,
            )
            notification.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Notification.DoesNotExist:
            return Response(
                {"error": "Notification not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
