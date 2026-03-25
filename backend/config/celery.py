"""
Celery configuration for MegaStore.

Sets up the Celery application with Django integration,
task auto-discovery, and periodic task scheduling.
"""

import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

app = Celery("megastore")

# Load configuration from Django settings, using the CELERY_ prefix
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks in all installed apps
app.autodiscover_tasks()

# =============================================================================
# Periodic Tasks (Celery Beat Schedule)
# =============================================================================

app.conf.beat_schedule = {
    # Check for abandoned carts and send reminder emails
    "send-abandoned-cart-reminders": {
        "task": "apps.orders.tasks.send_abandoned_cart_reminders",
        "schedule": crontab(hour=10, minute=0),  # Daily at 10:00 AM UTC
        "options": {"queue": "emails"},
    },
    # Clean up expired carts (older than 30 days)
    "cleanup-expired-carts": {
        "task": "apps.cart.tasks.cleanup_expired_carts",
        "schedule": crontab(hour=3, minute=0),  # Daily at 3:00 AM UTC
        "options": {"queue": "default"},
    },
    # Generate daily sales report for vendors
    "generate-daily-sales-report": {
        "task": "apps.orders.tasks.generate_daily_sales_report",
        "schedule": crontab(hour=6, minute=0),  # Daily at 6:00 AM UTC
        "options": {"queue": "default"},
    },
    # Check for low stock products and notify vendors
    "check-low-stock-alerts": {
        "task": "apps.products.tasks.check_low_stock_alerts",
        "schedule": crontab(hour="*/6", minute=0),  # Every 6 hours
        "options": {"queue": "emails"},
    },
    # Process pending payouts to vendors
    "process-vendor-payouts": {
        "task": "apps.payments.tasks.process_pending_payouts",
        "schedule": crontab(hour=0, minute=0, day_of_week=1),  # Weekly on Monday
        "options": {"queue": "payments"},
    },
}


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task to verify Celery is operational."""
    print(f"Request: {self.request!r}")
