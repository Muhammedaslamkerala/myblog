# users/utils.py
import logging
import random
import string
from django.conf import settings
from django.utils import timezone
from django.core.mail import send_mail
from django.template.loader import render_to_string
from .models import CustomUser, EmailNotification, LoginLog

logger = logging.getLogger(__name__)

def generate_otp(length=6):
    """Generate a random OTP of a given length."""
    return ''.join(random.choices(string.digits, k=length))

# ========== 🔔 ASYNCHRONOUS NOTIFICATION DISPATCHER ==========

def create_and_dispatch_notification(user_id, notification_type, subject_template, context=None):
    """
    General reusable function to create a notification record and
    dispatch a background task to send it.
    """
    # Import the task here to avoid circular dependencies at startup
    from .tasks import send_email_notification_task
    
    try:
        user = CustomUser.objects.get(id=user_id)
        context = context or {}

        # Check user preference before creating the notification
        if not getattr(user, "email_notifications", True):
            logger.info(f"User {user.email} has notifications disabled. Skipping '{notification_type}'.")
            return None

        notification = EmailNotification.objects.create(
            user=user,
            notification_type=notification_type,
            subject=subject_template,
            context_data=context,
        )
        
        # Dispatch the background task with the new notification's ID
        send_email_notification_task.delay(notification.id)
        
        logger.info(f"Dispatched '{notification_type}' notification task (ID: {notification.id}) for {user.email}")
        return notification
        
    except CustomUser.DoesNotExist:
        logger.error(f"Failed to create notification: User with ID {user_id} not found.")
        return None
    except Exception as e:
        logger.exception(f"Failed to create/dispatch '{notification_type}' notification for user ID {user_id}")
        return None

# ========== 🗣️ NOTIFICATION HELPER FUNCTIONS (Asynchronous) ==========

def send_login_notification(user_id, login_log_id):
    """Prepare and dispatch a login notification task."""
    try:
        login_log = LoginLog.objects.get(id=login_log_id)
        site_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')
        
        context_data = {
            'login_log': {
                'ip_address': login_log.ip_address,
                'user_agent': login_log.user_agent,
                'login_time': login_log.login_time.strftime('%Y-%m-%d %H:%M:%S %Z'),
                'location': getattr(login_log, 'location', 'Unknown'),
            },
            'security_link': f'{site_url.rstrip("/")}/users/change-password/',
        }
        
        notification = create_and_dispatch_notification(
            user_id, 
            'login', 
            "Security Alert: New Login to Your Account",
            context_data
        )

        if notification:
            login_log.notification_sent = True
            login_log.save(update_fields=['notification_sent'])
            return True
        return False
    except LoginLog.DoesNotExist:
        logger.error(f"Cannot send login notification: LoginLog with ID {login_log_id} not found.")
        return False


def send_welcome_email(user_id):
    """Prepare and dispatch a welcome email task."""
    site_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')
    user = CustomUser.objects.get(id=user_id)
    context_data = {
        'site_name': getattr(settings, 'SITE_NAME', 'MyBlog'),
        'login_url': f'{site_url.rstrip("/")}/users/login/',
        'profile_url': f'{site_url.rstrip("/")}/users/profile/{user.username}/',
    }
    notification = create_and_dispatch_notification(
        user_id, 
        'welcome', 
        f"Welcome to {getattr(settings, 'SITE_NAME', 'MyBlog')}!",
        context_data
    )
    return bool(notification)


def send_new_follower_notification(follow_instance):
    """Prepare and dispatch a new follower notification."""
    followed_user = follow_instance.following
    follower_user = follow_instance.follower
    site_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')
    
    context_data = {
        'follower': {
            'username': follower_user.username,
            'profile_link': f'{site_url.rstrip("/")}/users/profile/{follower_user.username}/',
        },
    }
    notification = create_and_dispatch_notification(
        followed_user.id, 
        'new_follower',
        f"You have a new follower: {follower_user.username}",
        context_data
    )
    return bool(notification)


def send_account_update_notification(user_id, changes=None):
    """Send account update notification asynchronously."""
    site_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')
    context_data = {
        'changed_field': ', '.join(changes.keys()) if changes else 'your account settings',
        'timestamp': timezone.now().strftime('%Y-%m-%d %H:%M:%S UTC'),
        'security_link': f'{site_url.rstrip("/")}/users/change-password/',
        'site_name': getattr(settings, 'SITE_NAME', "MyBlog"),
    }
    notification = create_and_dispatch_notification(
        user_id, 
        'account_update', 
        "Your Account Information Was Updated",
        context_data
    )
    return bool(notification)


# ========== ✉️ DIRECT EMAIL FUNCTIONS (Synchronous) ==========
# These functions send emails directly and are used for critical,
# immediate actions like OTP verification. They do not use the Celery queue.

def send_otp_email(user, otp):
    """Send OTP verification email using rendered templates directly."""
    try:
        subject = f'Verify your email - {settings.SITE_NAME or "MyBlog"}'
        context = {
            'user': user, 'otp': otp, 'site_name': settings.SITE_NAME or 'MyBlog',
        }
        html_content = render_to_string('emails/otp_email.html', context)
        text_content = render_to_string('emails/otp_email.txt', context)
        
        send_mail(
            subject, text_content, settings.DEFAULT_FROM_EMAIL, [user.email],
            fail_silently=False, html_message=html_content,
        )
        logger.info(f"OTP sent directly to {user.email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send OTP email directly: {e}")
        return False


def send_email_change_verification(user, new_email, otp):
    """Send OTP to a new email address for verification directly."""
    try:
        subject = f'Verify your new email - {settings.SITE_NAME or "MyBlog"}'
        context = { 'user': user, 'otp': otp, 'new_email': new_email }
        html_content = render_to_string('emails/email_change_otp.html', context)
        text_content = render_to_string('emails/email_change_otp.txt', context)
        
        send_mail(
            subject, text_content, settings.DEFAULT_FROM_EMAIL, [new_email],
            fail_silently=False, html_message=html_content,
        )
        logger.info(f"Email change OTP sent directly to {new_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email change OTP directly: {e}")
        return False