from django.db import models
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from django.utils import timezone
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class EmailNotification(models.Model):
    """Model to track all email notifications sent to users"""
    NOTIFICATION_TYPES = [
        ('login', 'Login Notification'),
        ('new_post', 'New Post Published'),
        ('new_comment', 'New Comment on Post'),
        ('comment_reply', 'New Reply to Comment'),
        ('new_like', 'Post Liked'),
        ('new_follower', 'New Follower'),
        ('password_reset', 'Password Reset'),
        ('account_update', 'Account Updated'),
        ('welcome', 'Welcome Email'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
    ]
    
    user = models.ForeignKey(
        'CustomUser',
        on_delete=models.CASCADE,
        related_name='email_notifs'  # Fixed: was 'email_notifs'
    )
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    subject = models.CharField(max_length=255)
    content = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    sent_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Store additional context as JSON
    context_data = models.JSONField(default=dict, blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Email Notification'
        verbose_name_plural = 'Email Notifications'
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['notification_type', 'status']),
        ]
    
    def __str__(self):
        return f"{self.get_notification_type_display()} to {self.user.email} - {self.get_status_display()}"
    
    def get_context_data(self):
        """Get context data"""
        return self.context_data or {}
    
    def set_context_data(self, data):
        """Store context data"""
        self.context_data = data or {}
    
    def send(self):
        """
        Sends the email notification.
        This method should be called from a background task.
        """
        logger.info(f"Initiating send for notification ID {self.id} to {self.user.email}")
        try:
            # Universal context available to all email templates
            context = {
                'user': self.user,
                'notification': self,
                'site_name': getattr(settings, 'SITE_NAME', 'MyBlog'),
                'site_url': getattr(settings, 'SITE_URL', 'http://localhost:8000'),
                **self.get_context_data()
            }

            # Render HTML and plain text templates
            html_template = f'emails/{self.notification_type}.html'
            text_template = f'emails/{self.notification_type}.txt'
            
            html_content = render_to_string(html_template, context)
            text_content = render_to_string(text_template, context)

            msg = EmailMultiAlternatives(
                subject=self.subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[self.user.email],
            )
            msg.attach_alternative(html_content, "text/html")
            
            # The send() method returns the number of successfully sent emails (1 or 0)
            sent_count = msg.send(fail_silently=False)

            if sent_count > 0:
                self.status = 'sent'
                self.sent_at = timezone.now()
                self.error_message = ''
                self.save(update_fields=['status', 'sent_at', 'error_message'])
                logger.info(f"Email sent successfully to {self.user.email} for notification ID {self.id}")
                return True
            else:
                # This case is rare if fail_silently=False, as an exception is usually raised
                self.status = 'failed'
                self.error_message = 'Django send_mail() returned 0 messages sent.'
                self.save(update_fields=['status', 'error_message'])
                logger.error(f"Email send method returned 0 for {self.user.email} (ID: {self.id})")
                return False

        except Exception as e:
            logger.exception(f"Failed to send '{self.notification_type}' email to {self.user.email} (ID: {self.id})")
            self.status = 'failed'
            self.error_message = str(e)
            self.save(update_fields=['status', 'error_message'])
            return False

class LoginLog(models.Model):
    """Model to track user logins for security notifications"""
    user = models.ForeignKey(
        'CustomUser',
        on_delete=models.CASCADE,
        related_name='login_logs'
    )
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    location = models.CharField(max_length=255, blank=True)
    login_time = models.DateTimeField(auto_now_add=True)
    is_suspicious = models.BooleanField(default=False)
    notification_sent = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-login_time']
        verbose_name = 'Login Log'
        verbose_name_plural = 'Login Logs'
    
    def __str__(self):
        return f"{self.user.username} - {self.login_time} - {self.ip_address}"