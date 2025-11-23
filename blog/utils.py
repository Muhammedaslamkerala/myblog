# users/utils.py
from users.models.follow import Follow
from users.models import EmailNotification 
from django.conf import settings
import logging

# Import the task to dispatch it
from users.tasks import send_email_notification_task

logger = logging.getLogger(__name__)


def send_post_notification(post):
    """
    Creates and dispatches notifications for a new post to all followers.
    """
    try:
        site_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')
        # Get followers of the post author who have email notifications enabled
        followers = Follow.objects.filter(
            following=post.author,
            follower__email_notifications=True
        ).select_related('follower')  # Optimize DB query

        dispatch_count = 0
        for follow in followers:
            user = follow.follower
            
            # Create the notification object in the database
            try:
                notification = EmailNotification.objects.create(
                    user=user,
                    notification_type='new_post',
                    subject=f"New post from {post.author.get_display_name()}",
                    context_data={
                        "post": {
                            "title": post.title,
                            "excerpt": getattr(post, "excerpt", "")[:200],
                            "author_name": post.author.get_display_name(),
                            "url": f"{site_url.rstrip('/')}{post.get_absolute_url()}",
                        }
                    }
                )
                
                # Dispatch the background task with the notification's ID
                send_email_notification_task.delay(notification.id)
                dispatch_count += 1
            except Exception as e:
                logger.error(f"Failed to create/dispatch notification for user {user.email}: {e}")
                continue

        logger.info(f"Dispatched {dispatch_count} 'new_post' notification tasks for post '{post.title}'.")
        return dispatch_count

    except Exception as e:
        logger.exception(f"Failed to dispatch post notifications for post ID {post.id}")
        return 0


def _create_and_dispatch_single_notification(user, notification_type, subject, context_data):
    """Helper to create and dispatch a single notification."""
    if not getattr(user, 'email_notifications', False):
        logger.info(f"Skipping '{notification_type}' for {user.email} (notifications disabled).")
        return False
    
    try:
        notification = EmailNotification.objects.create(
            user=user,
            notification_type=notification_type,
            subject=subject,
            context_data=context_data,
        )
        send_email_notification_task.delay(notification.id)
        logger.info(f"Dispatched '{notification_type}' task (ID: {notification.id}) to {user.email}")
        return True
    except Exception as e:
        logger.error(f"Failed to create/dispatch {notification_type} notification: {e}")
        return False


def send_comment_notification(comment):
    """Notifies a post author of a new comment asynchronously."""
    site_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')
    context = {
        'comment': {
            'author_name': comment.author.get_display_name(),
            'content': comment.body[:200],  # Truncate long comments
            'post_title': comment.post.title,
            'url': f"{site_url.rstrip('/')}{comment.post.get_absolute_url()}#comment-{comment.id}",
        }
    }
    return _create_and_dispatch_single_notification(
        user=comment.post.author,
        notification_type='new_comment',
        subject=f"New comment on your post '{comment.post.title}'",
        context_data=context
    )


def send_like_notification(like):
    """Notifies a post author of a new like asynchronously."""
    site_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')
    context = {
        'like': {
            'user_name': like.user.get_display_name(),
            'post_title': like.post.title,
            'url': f"{site_url.rstrip('/')}{like.post.get_absolute_url()}",
        }
    }
    return _create_and_dispatch_single_notification(
        user=like.post.author,
        notification_type='new_like',
        subject=f"Your post '{like.post.title}' got a new like!",
        context_data=context
    )


def send_reply_notification(reply):
    """Notifies a parent comment author of a new reply asynchronously."""
    if not hasattr(reply, 'parent') or not reply.parent:
        return False
        
    site_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')
    context = {
        'reply': {
            'author_name': reply.author.get_display_name(),
            'content': reply.body[:200],  # Truncate long replies
            'parent_comment_excerpt': reply.parent.body[:100] + ('...' if len(reply.parent.body) > 100 else ''),
            'post_title': reply.post.title,
            'url': f"{site_url.rstrip('/')}{reply.post.get_absolute_url()}#comment-{reply.id}",
        }
    }
    return _create_and_dispatch_single_notification(
        user=reply.parent.author,
        notification_type='comment_reply',
        subject=f"New reply to your comment on '{reply.post.title}'",
        context_data=context
    )