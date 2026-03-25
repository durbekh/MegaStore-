"""URL patterns for the notifications application."""

from django.urls import path

from . import views

app_name = "notifications"

urlpatterns = [
    path("", views.NotificationListView.as_view(), name="notification-list"),
    path("count/", views.NotificationCountView.as_view(), name="notification-count"),
    path("mark-read/", views.NotificationMarkReadView.as_view(), name="notification-mark-read"),
    path("<uuid:pk>/", views.NotificationDetailView.as_view(), name="notification-detail"),
    path("<uuid:pk>/delete/", views.NotificationDeleteView.as_view(), name="notification-delete"),
]
