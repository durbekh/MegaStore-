"""
Celery tasks for the accounts application.

Handles asynchronous operations like sending welcome emails,
verification emails, and account-related notifications.
"""

import logging

from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)

User = get_user_model()


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    queue="emails",
)
def send_welcome_email(self, user_id):
    """
    Send a welcome email to a newly registered user.

    Retries up to 3 times with a 60-second delay between attempts.
    """
    try:
        user = User.objects.get(id=user_id)

        subject = f"Welcome to {settings.PLATFORM_NAME}!"
        message = (
            f"Hi {user.first_name},\n\n"
            f"Welcome to {settings.PLATFORM_NAME}! We're excited to have you.\n\n"
        )

        if user.is_vendor:
            message += (
                "Your vendor account has been created and is pending approval. "
                "You'll receive a notification once your account is reviewed.\n\n"
                "In the meantime, feel free to explore the platform and set up "
                "your store profile.\n\n"
            )
        else:
            message += (
                "Start exploring our marketplace and discover amazing products "
                "from vendors around the world.\n\n"
            )

        message += (
            f"If you have any questions, don't hesitate to reach out.\n\n"
            f"Best regards,\n"
            f"The {settings.PLATFORM_NAME} Team"
        )

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )

        logger.info("Welcome email sent to: %s", user.email)

    except User.DoesNotExist:
        logger.error("User %s not found for welcome email", user_id)
    except Exception as exc:
        logger.error("Failed to send welcome email to user %s: %s", user_id, exc)
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    queue="emails",
)
def send_email_verification(self, user_id, verification_url):
    """Send an email verification link to the user."""
    try:
        user = User.objects.get(id=user_id)

        subject = f"Verify your {settings.PLATFORM_NAME} email"
        message = (
            f"Hi {user.first_name},\n\n"
            f"Please verify your email address by clicking the link below:\n\n"
            f"{verification_url}\n\n"
            f"This link will expire in 24 hours.\n\n"
            f"If you didn't create an account, please ignore this email.\n\n"
            f"Best regards,\n"
            f"The {settings.PLATFORM_NAME} Team"
        )

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )

        logger.info("Verification email sent to: %s", user.email)

    except User.DoesNotExist:
        logger.error("User %s not found for verification email", user_id)
    except Exception as exc:
        logger.error("Failed to send verification email to user %s: %s", user_id, exc)
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    queue="emails",
)
def send_password_reset_email(self, user_id, reset_url):
    """Send a password reset link to the user."""
    try:
        user = User.objects.get(id=user_id)

        subject = f"Reset your {settings.PLATFORM_NAME} password"
        message = (
            f"Hi {user.first_name},\n\n"
            f"We received a request to reset your password. "
            f"Click the link below to set a new password:\n\n"
            f"{reset_url}\n\n"
            f"This link will expire in 1 hour.\n\n"
            f"If you didn't request a password reset, please ignore this email.\n\n"
            f"Best regards,\n"
            f"The {settings.PLATFORM_NAME} Team"
        )

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )

        logger.info("Password reset email sent to: %s", user.email)

    except User.DoesNotExist:
        logger.error("User %s not found for password reset email", user_id)
    except Exception as exc:
        logger.error("Failed to send password reset email to user %s: %s", user_id, exc)
        raise self.retry(exc=exc)


@shared_task(queue="emails")
def send_vendor_approval_notification(user_id, approved=True, reason=""):
    """Notify a vendor that their account has been approved or rejected."""
    try:
        user = User.objects.get(id=user_id)

        if approved:
            subject = f"Your {settings.PLATFORM_NAME} vendor account is approved!"
            message = (
                f"Hi {user.first_name},\n\n"
                f"Great news! Your vendor account has been approved. "
                f"You can now start listing products on {settings.PLATFORM_NAME}.\n\n"
                f"Log in to your dashboard to get started.\n\n"
                f"Best regards,\n"
                f"The {settings.PLATFORM_NAME} Team"
            )
        else:
            subject = f"Update on your {settings.PLATFORM_NAME} vendor application"
            message = (
                f"Hi {user.first_name},\n\n"
                f"Thank you for your interest in selling on {settings.PLATFORM_NAME}. "
                f"Unfortunately, we were unable to approve your vendor application "
                f"at this time.\n\n"
            )
            if reason:
                message += f"Reason: {reason}\n\n"
            message += (
                f"You may reapply after addressing the concerns mentioned above.\n\n"
                f"Best regards,\n"
                f"The {settings.PLATFORM_NAME} Team"
            )

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )

        logger.info("Vendor approval notification sent to: %s (approved=%s)", user.email, approved)

    except User.DoesNotExist:
        logger.error("User %s not found for vendor approval notification", user_id)
    except Exception as exc:
        logger.error("Failed to send vendor approval notification: %s", exc)
