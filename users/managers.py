from django.contrib.auth.base_user import BaseUserManager
from django.utils.translation import gettext_lazy as _
import re

class CustomUserManager(BaseUserManager):
    """
    Custom user model manager where email is the unique identifier
    for authentication instead of usernames.
    """
    def create_user(self, email, username, password=None, **extra_fields):
        """
        Create and save a User with the given email, username and password.
        """
        if not email:
            raise ValueError(_('The Email must be set'))
        if not username:
            raise ValueError(_('The Username must be set'))
        
        # Validate username format
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            raise ValueError(_('Username can only contain letters, numbers, and underscores.'))
        
        if len(username) < 3:
            raise ValueError(_('Username must be at least 3 characters long.'))
        
        if len(username) > 30:
            raise ValueError(_('Username must be 30 characters or fewer.'))
        
        # Check if username already exists (case-insensitive)
        if self.model.objects.filter(username__iexact=username).exists():
            raise ValueError(_('A user with that username already exists.'))
        
        email = self.normalize_email(email)
        username = username.lower()  # Convert to lowercase for consistency
        
        user = self.model(
            email=email,
            username=username,
            **extra_fields
        )
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, username, password=None, **extra_fields):
        """
        Create and save a SuperUser with the given email, username and password.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))
        
        return self.create_user(email, username, password, **extra_fields)
    
    def get_by_natural_key(self, email):
        """
        Get user by email (natural key for authentication)
        """
        return self.get(email=email)
    
    def get_by_username(self, username):
        """
        Get user by username (case-insensitive)
        """
        return self.get(username__iexact=username)