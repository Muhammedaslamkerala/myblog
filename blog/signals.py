# blog/signals.py
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import Post, PostLike, Comment
import logging

logger = logging.getLogger(__name__)

@receiver(pre_save, sender=Post)
def auto_generate_summary(sender, instance, **kwargs):
    """Generate and store AI summary before saving"""
    is_new = instance._state.adding
    # Generate if new, empty, or body changed
    if (is_new or not instance.summary) and instance.body:
        from .ai_services import ai_service
        from django.utils.html import strip_tags
        
        clean_body = strip_tags(instance.body).strip()
        if clean_body:  # Only generate if there's actual text content
            summary = ai_service.generate_summary(clean_body, num_lines=3)
            if summary and summary != "Unable to generate summary.":
                instance.summary = summary
                logger.info(f"Generated and stored summary for post: {instance.title}")
        else:
            logger.warning(f"Post '{instance.title}' has no text content for summary generation")

@receiver(post_save, sender=Post)
def auto_generate_ai_features(sender, instance, created, **kwargs):
    """Generate tags, category, and prepare RAG after post creation"""
    if instance.status == 'public':
        from .tasks import (
            generate_tags_task,
            suggest_category_task,
            prepare_rag_data_task,
        )
        from users.tasks import send_email_notification_task  # Import Celery task, not function
        
        # Generate tags
        if not instance.tags.exists() and not instance.ai_generated_tags:
            try:
                generate_tags_task.delay(str(instance.id))
                logger.info(f"Tag generation task queued for post: {instance.title}")
            except Exception as e:
                logger.error(f"Failed to queue tag generation for post {instance.id}: {e}")
        
        # Suggest category
        if not instance.categories.exists() and not instance.ai_generated_category:
            try:
                suggest_category_task.delay(str(instance.id))
                logger.info(f"Category suggestion task queued for post: {instance.title}")
            except Exception as e:
                logger.error(f"Failed to queue category suggestion for post {instance.id}: {e}")
        
        # Prepare RAG data (only if there's text content)
        from django.utils.html import strip_tags
        clean_body = strip_tags(instance.body).strip()
        if clean_body and not instance.content_chunks:
            try:
                prepare_rag_data_task.delay(str(instance.id))
                logger.info(f"RAG preparation task queued for post: {instance.title}")
            except Exception as e:
                logger.error(f"Failed to queue RAG preparation for post {instance.id}: {e}")
        
        # Send notifications to followers (FIXED: import from users.utils, call directly)
        if created:
            try:
                from users.utils import send_post_notification
                send_post_notification(instance)
                logger.info(f"Post notification dispatched for: '{instance.title}'")
            except Exception as e:
                logger.error(f"Failed to dispatch post notification for post ID {instance.id}: {e}")


@receiver(post_save, sender=Comment)
def handle_new_comment(sender, instance, created, **kwargs):
    """Send notifications for new comments and replies."""
    if created:
        try:
            from blog.utils import send_comment_notification, send_reply_notification
            
            # Check if this is a reply to another comment
            if hasattr(instance, 'parent') and instance.parent:
                # Notify the parent comment author if they are not the one replying
                if instance.author != instance.parent.author:
                    send_reply_notification(instance)
                    logger.info(f"Reply notification dispatched for comment {instance.id}")
            else:
                # This is a top-level comment. Notify the post author.
                # Only notify if the commenter is not the post author.
                if instance.author != instance.post.author:
                    send_comment_notification(instance)
                    logger.info(f"Comment notification dispatched for comment {instance.id}")
        except Exception as e:
            logger.error(f"Failed to dispatch comment/reply notification for comment ID {instance.id}: {e}")


@receiver(post_save, sender=PostLike)
def handle_new_like(sender, instance, created, **kwargs):
    """Send notification when someone likes a post."""
    # Only notify if the person who liked is not the post author.
    if created and instance.user != instance.post.author:
        try:
            from blog.utils import send_like_notification
            send_like_notification(instance)
            logger.info(f"Like notification dispatched for post {instance.post.id}")
        except Exception as e:
            logger.error(f"Failed to dispatch like notification for like ID {instance.id}: {e}")