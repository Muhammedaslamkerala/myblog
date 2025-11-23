from django.db import models
from django.contrib.auth import get_user_model
from .post import Post

User = get_user_model()

class Bookmark(models.Model):
    """A model to store a user's bookmarked posts."""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='bookmarks'
    )
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='bookmarks'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'post')
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.username} bookmarked "{self.post.title}"'
