"""
Signals for the accounts application.

Handles automatic profile creation and updates triggered
by user model changes.
"""

import logging

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import CustomerProfile, User, VendorProfile

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Automatically create the appropriate profile when a new user is created.

    - CUSTOMER role: creates a CustomerProfile
    - VENDOR role: creates a VendorProfile (if not already created during registration)
    """
    if not created:
        return

    if instance.role == User.Role.CUSTOMER:
        profile, profile_created = CustomerProfile.objects.get_or_create(user=instance)
        if profile_created:
            logger.info("CustomerProfile created for user: %s", instance.email)

    elif instance.role == User.Role.VENDOR:
        # VendorProfile may already be created in the registration serializer
        # with store_name. Only create here if it does not exist.
        if not VendorProfile.objects.filter(user=instance).exists():
            logger.debug(
                "VendorProfile not auto-created for %s (expected from serializer)",
                instance.email,
            )


@receiver(post_save, sender=User)
def update_last_login_log(sender, instance, created, **kwargs):
    """Log when a user's last_login is updated (on login)."""
    if not created and instance.last_login:
        logger.debug("User login: %s at %s", instance.email, instance.last_login)
