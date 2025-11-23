# users/signals.py
from django.db.models.signals import post_save
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
from .models import LoginLog, EmailNotification
from users.models.follow import Follow
from .models import Profile, CustomUser
from .utils import (
    send_login_notification,
    send_welcome_email,
    send_new_follower_notification,
)
import logging

logger = logging.getLogger(__name__)




# Signal to auto-create Profile when CustomUser is created
@receiver(post_save, sender=CustomUser)
def create_user_profile(sender, instance, created, **kwargs):
    """Automatically create a Profile when a new user is created"""
    if created:
        
        Profile.objects.get_or_create(user=instance)


@receiver(post_save, sender=CustomUser)
def save_user_profile(sender, instance, **kwargs):
    """Save the profile when the user is saved"""
    if hasattr(instance, 'profile'):
        instance.profile.save()


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_notifications(sender, instance, created, **kwargs):
    """
    Handle post-save actions for CustomUser.
    - Send welcome email to new, active, and verified users.
    """
    if created and instance.is_active and getattr(instance, 'email_verified', False):
        try:
            # This function will create the notification and dispatch the task
            send_welcome_email(instance.id)
            logger.info(f"Welcome email task dispatched for: {instance.email}")
        except Exception as e:
            logger.error(f"Failed to dispatch welcome email for {instance.email}: {e}")


@receiver(user_logged_in)
def handle_user_login(sender, request, user, **kwargs):
    """
    Handle user login events.
    - Create login log.
    - Detect suspicious logins and send a security notification.
    """
    try:
        # Get IP address, handling proxies
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(',')[0].strip()
        else:
            ip_address = request.META.get('REMOTE_ADDR', '')

        user_agent = request.META.get('HTTP_USER_AGENT', '')

        login_log = LoginLog.objects.create(
            user=user, ip_address=ip_address, user_agent=user_agent
        )
        logger.info(f"User logged in: {user.username} from {ip_address}")

        # Check if the user has email notifications enabled
        if not getattr(user, "email_notifications", False):
            logger.info(f"Email notifications disabled for user: {user.email}. Skipping login check.")
            return

        # Check for suspicious activity
        thirty_days_ago = timezone.now() - timedelta(days=30)
        recent_logins = LoginLog.objects.filter(
            user=user, login_time__gte=thirty_days_ago
        ).exclude(id=login_log.id)

        is_new_ip = not recent_logins.filter(ip_address=ip_address).exists()
        is_new_device = not recent_logins.filter(user_agent=user_agent).exists()

        if is_new_ip or is_new_device:
            login_log.is_suspicious = True
            login_log.save(update_fields=['is_suspicious'])
            
            logger.info(
                f"Suspicious login detected for {user.username}: "
                f"new_ip={is_new_ip}, new_device={is_new_device}"
            )
            # Dispatch the notification task
            send_login_notification(user.id, login_log.id)
        else:
            logger.info(f"Normal login for {user.username} from known IP/device.")

    except Exception as e:
        logger.exception(f"Error in handle_user_login signal for user {user.username}")


@receiver(post_save, sender=Follow)
def handle_new_follower(sender, instance, created, **kwargs):
    """
    Handle new follower creation.
    - Send a notification to the user who was followed.
    """
    if created:
        try:
            # The utility function handles checking preferences and dispatching the task
            send_new_follower_notification(instance)
            logger.info(f"New follower notification dispatched for: {instance.follower.username} -> {instance.following.username}")
        except Exception as e:
            logger.error(f"Failed to dispatch new follower notification for follow ID {instance.id}: {e}")