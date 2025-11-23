from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator
from django.conf import settings
import re

from ..managers import CustomUserManager
from .follow import Follow


class CustomUser(AbstractBaseUser, PermissionsMixin):
    """Custom user model for authentication and follow system"""

    username_validator = RegexValidator(
        regex=r'^[a-zA-Z0-9_]+$',
        message='Username can only contain letters, numbers, and underscores.',
        code='invalid_username'
    )

    username = models.CharField(
        _('Username'),
        max_length=30,
        unique=True,
        null=True,  # temporarily allow null during creation
        validators=[username_validator],
        help_text=_('Required. 30 characters or fewer. Letters, numbers and underscores only.'),
        error_messages={'unique': _("A user with that username already exists.")},
    )

    email = models.EmailField(_('Email address'), unique=True)
    first_name = models.CharField(max_length=50, blank=True)
    last_name = models.CharField(max_length=50, blank=True)

    # Email verification fields
    email_verified = models.BooleanField(default=False)
    email_verified_at = models.DateTimeField(null=True, blank=True)

    # Preferences
    email_notifications = models.BooleanField(default=True)

    # Status fields
    is_active = models.BooleanField(_('Active'), default=True)
    is_staff = models.BooleanField(_('Staff status'), default=False)
    is_superuser = models.BooleanField(_('SuperUser status'), default=False)

    # Timestamps
    date_joined = models.DateTimeField(_("Date joined"), default=timezone.now)
    last_login = models.DateTimeField(_("Last login"), blank=True, null=True)

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')

    def __str__(self):
        return self.get_display_name()

    # ===== Display helpers =====
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def get_short_name(self):
        return self.first_name or self.username

    def get_display_name(self):
        return self.get_full_name() or f"@{self.username}"

    def clean(self):
        super().clean()
        if self.username:
            self.username = self.username.lower()

    def save(self, *args, **kwargs):
        """Auto-generate username from email if missing"""
        if not self.username and self.email:
            base_username = re.sub(r'[^a-zA-Z0-9_]', '', self.email.split('@')[0])
            unique_username = base_username
            counter = 1
            while CustomUser.objects.filter(username=unique_username).exclude(pk=self.pk).exists():
                unique_username = f"{base_username}{counter}"
                counter += 1
            self.username = unique_username.lower()

        self.full_clean()
        super().save(*args, **kwargs)

    # ===== Follow system helpers =====
    def follow(self, user):
        if user != self:
            Follow.objects.get_or_create(follower=self, following=user)

    def unfollow(self, user):
        Follow.objects.filter(follower=self, following=user).delete()

    def is_following(self, user):
        return Follow.objects.filter(follower=self, following=user).exists()

    def is_followed_by(self, user):
        if not user or not user.is_authenticated:
            return False
        return Follow.objects.filter(follower=user, following=self).exists()

    def followers_count(self):
        return self.followers.count()

    def following_count(self):
        return self.following.count()




