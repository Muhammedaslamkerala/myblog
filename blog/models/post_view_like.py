from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from .post import Post

User = get_user_model()

class PostView(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='post_views')
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        unique_together = ['post', 'ip_address']

class PostLike(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='post_likes')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['post', 'user']
