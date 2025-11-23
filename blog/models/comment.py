from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from django.utils import timezone
from django.core.exceptions import ValidationError

User = get_user_model()

class Comment(models.Model):
    """User comments and replies for blog posts."""
    post = models.ForeignKey(
        'blog.Post',
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name=_("Post"),
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='user_comments',
        verbose_name=_("Author"),
    )
    body = models.TextField(verbose_name=_("Comment"))
    published_date = models.DateTimeField(auto_now_add=True, verbose_name=_("Published Date"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))
    
    # Moderation flags
    is_approved = models.BooleanField(default=True, verbose_name=_("Is Approved"))
    is_flagged = models.BooleanField(default=False, verbose_name=_("Is Flagged"))
    flagged_reason = models.CharField(
        max_length=255, blank=True, null=True, verbose_name=_("Flagged Reason")
    )
    
    # Reply system
    parent = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='replies',
        verbose_name=_("Parent Comment"),
    )

    class Meta:
        verbose_name = _("Comment")
        verbose_name_plural = _("Comments")
        ordering = ['-published_date']
        indexes = [
            models.Index(fields=['post', '-published_date']),
            models.Index(fields=['author', '-published_date']),
            models.Index(fields=['is_approved', 'is_flagged']),
            models.Index(fields=['parent']),
        ]

    def __str__(self) -> str:
        name = self.author.get_full_name() or self.author.username
        return f"{name} - {self.post.title[:50]}"

    def clean(self):
        """Validate comment constraints."""
        super().clean()
        
        # Prevent deeply nested replies (optional depth limit)
        if self.parent:
            depth = 0
            current = self.parent
            max_depth = 3  # Adjust as needed
            
            while current and depth < max_depth:
                depth += 1
                current = current.parent
            
            if depth >= max_depth:
                raise ValidationError(_("Reply nesting is too deep. Maximum depth is {}.").format(max_depth))
            
            # Ensure parent belongs to same post
            if self.parent.post != self.post:
                raise ValidationError(_("Parent comment must belong to the same post."))

    def get_absolute_url(self):
        return f"{self.post.get_absolute_url()}#comment-{self.id}"

    @property
    def is_reply(self):
        return self.parent is not None
    
    @property
    def is_edited(self):
        """Check if comment was edited after initial publication."""
        return self.updated_at > self.published_date + timezone.timedelta(seconds=1)
    
    def get_reply_count(self):
        """Get total number of replies (including nested)."""
        count = self.replies.count()
        for reply in self.replies.all():
            count += reply.get_reply_count()
        return count

    def save(self, *args, **kwargs):
        """
        Optional AI moderation hook:
        Automatically flag toxic or spam comments using a helper.
        If you don't use AI yet, this will do nothing.
        """
        # Run validation
        if not kwargs.pop('skip_validation', False):
            self.full_clean()
        
        try:
            from ..utils import analyze_comment  
            result = analyze_comment(self.body)
            if result:
                self.is_flagged = result.get("is_toxic", False) or result.get("is_spam", False)
                self.flagged_reason = result.get("reason", "")
        except ImportError:
            # Skip if AI module not available
            pass
        
        super().save(*args, **kwargs)