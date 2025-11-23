# views.py
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from users.models.follow import Follow
from ..models import EmailNotification
import logging

logger = logging.getLogger(__name__)

@login_required
def notification_center(request):
    """Display user's email notifications"""
    notification_type = request.GET.get('type', 'all')
    
    # Use the correct related_name as defined in the model
    notifications = request.user.email_notifs.all()

    if notification_type != 'all':
        notifications = notifications.filter(notification_type=notification_type)

    # Pagination
    paginator = Paginator(notifications, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'emails/notification_center.html', {
        'notifications': page_obj,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        'current_type': notification_type,
    })


@login_required
@require_http_methods(["POST"])
def resend_notification(request, notification_id):
    """Resend a failed notification asynchronously via Celery."""
    # Import the task here to avoid circular dependency issues
    from ..tasks import send_email_notification_task

    try:
        notification = get_object_or_404(
            EmailNotification, 
            id=notification_id, 
            user=request.user,
            status='failed' # Only allow resending of failed notifications
        )

        # Reset status to 'pending' before dispatching the task
        notification.status = 'pending'
        notification.error_message = '' # Clear previous error
        notification.save(update_fields=['status', 'error_message'])

        # Dispatch the Celery task to handle the sending
        send_email_notification_task.delay(notification.id)

        return JsonResponse({
            'success': True, 
            'message': 'Resending notification... Status will update shortly.',
            'notification_id': notification.id,
            'new_status': 'Pending'
        })

    except EmailNotification.DoesNotExist:
         return JsonResponse({'success': False, 'message': 'Notification not found or you do not have permission to resend it.'}, status=404)
    except Exception as e:
        logger.exception(f"Error in resend_notification view for notification_id {notification_id}: {e}")
        return JsonResponse({'success': False, 'message': 'An unexpected error occurred.'}, status=500)


@login_required
def notification_preferences(request):
    """Handle notification preferences"""
    if request.method == 'POST':
        user = request.user
        # The value will be 'on' if checked, None otherwise.
        user.email_notifications = request.POST.get('email_notifications') == 'on'
        user.save()
        messages.success(request, 'Notification preferences updated successfully!')
        return redirect('users:account_settings')
    
    # If GET request, just redirect back.
    return redirect('users:account_settings')