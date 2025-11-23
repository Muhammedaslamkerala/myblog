from typing import Any


from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class Profile(models.Model):
    """Extended profile model for personalization and AI settings"""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile'
    )

    bio = models.TextField(_('Biography'), blank=True, null=True)
    website = models.URLField(blank=True)
    profile_picture = models.ImageField(
        _('Profile picture'),
        upload_to='profile_pictures/',
        blank=True,
        null=True
    )

    # Social Links
    twitter_url = models.URLField(blank=True)
    linkedin_url = models.URLField(blank=True)
    github_url = models.URLField(blank=True)

    # AI personalization / analytics
    interests = models.JSONField(default=list, blank=True)
    ai_preferences = models.JSONField(default=dict, blank=True)

    # Optional additional metadata
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile of {self.user.get_display_name()}"

    def get_profile_picture_url(self):
        if self.profile_picture and hasattr(self.profile_picture, 'url'):
            return self.profile_picture.url
        else:
            from django.conf import settings
            return settings.STATIC_URL + 'users/image/profile_pictures/default_picture.png'
