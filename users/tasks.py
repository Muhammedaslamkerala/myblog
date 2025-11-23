# users/tasks.py
from celery import shared_task
from django.apps import apps
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3, default_retry_delay=300) # Retry after 5 minutes
def send_email_notification_task(self, notification_id):
    """
    Celery task to send an email notification and notify the user via WebSocket.
    """
    # Use apps.get_model to avoid circular imports at module level
    EmailNotification = apps.get_model('users', 'EmailNotification')
    channel_layer = get_channel_layer()
    
    logger.info(f"--- Task started for EmailNotification ID: {notification_id} ---")

    try:
        notification = EmailNotification.objects.get(id=notification_id)
        logger.info(f"Found notification for user: {notification.user.email}")
    except EmailNotification.DoesNotExist:
        logger.error(f"FATAL: EmailNotification with id {notification_id} does not exist. Task cannot continue.")
        return False

    try:
        # Attempt to send the email using the model's method
        logger.info(f"Attempting to send email '{notification.notification_type}' to {notification.user.email}...")
        success = notification.send() # This method handles its own status updates and logging.

        if success:
            logger.info(f"SUCCESS: Email sent successfully to {notification.user.email} via model method.")
        else:
            # The .send() method already logged the error, but we log it here for task context.
            logger.error(f"FAILURE: notification.send() returned False for {notification.user.email}. Error: {notification.error_message}")

    except Exception as e:
        logger.exception(f"CRITICAL ERROR during email sending for notification {notification_id}: {e}")
        # Mark the notification as failed in the DB if an unexpected exception occurs
        notification.status = 'failed'
        notification.error_message = str(e)
        notification.save()
        # Retry the task for unexpected exceptions (e.g., SMTP server down)
        raise self.retry(exc=e)
    
    finally:
        # This block will run whether the email succeeded, failed, or an exception occurred.
        # It ensures the user always gets a real-time update.
        # We need to refresh the notification from the DB to get the latest status set by .send()
        notification.refresh_from_db()
        
        response_data = {
            'type': 'notification_status',
            'notification_id': notification.id,
            'status': notification.status,
            'status_display': notification.get_status_display(),
            'message': 'Notification sent successfully!' if notification.status == 'sent' else f'Failed: {notification.error_message}'
        }
        
        # Send the status update to the user-specific WebSocket group
        group_name = f"notifications_{notification.user.id}"
        logger.info(f"Attempting to send WebSocket update to group: {group_name}")
        try:
            async_to_sync(channel_layer.group_send)(
                group_name,
                {
                    "type": "send_notification_update", # This matches the consumer method name
                    "data": response_data,
                }
            )
            logger.info(f"WebSocket update sent successfully to group {group_name}.")
        except Exception as e:
            logger.error(f"Failed to send WebSocket update for notification {notification_id}: {e}")

    logger.info(f"--- Task for ID: {notification_id} finished. Final status: {notification.status} ---")
    return notification.status == 'sent'