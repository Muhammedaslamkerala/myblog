
import imghdr
from django.contrib.auth.forms import (
    UserCreationForm, AuthenticationForm
)
from django import forms
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError
from ..models.custom_user import CustomUser
import re

class RegistrationForm(UserCreationForm):
    first_name = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your first name'
        }),
        help_text='Required. 50 characters or fewer.'
    )

    last_name = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your last name'
        }),
        help_text='Required. 50 characters or fewer.'
    )

    username = forms.CharField(
        max_length=30,
        required=False,  # Optional since auto-generated
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Choose a unique username (optional)'
        }),
        help_text='30 characters or fewer. Letters, numbers and underscores only.'
    )

    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email address'
        }),
        help_text='Required. Enter a valid email address.'
    )

    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Create a strong password'
        }),
        help_text='Your password must contain at least 8 characters.'
    )

    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm your password'
        }),
        help_text='Enter the same password as before, for verification.'
    )

    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'username', 'email', 'password1', 'password2']

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if not username:
            return None  # Let the model auto-generate

        username = username.lower()
        if len(username) < 3:
            raise ValidationError('Username must be at least 3 characters long.')

        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            raise ValidationError('Username can only contain letters, numbers, and underscores.')

        if username[0].isdigit() or username[0] == '_':
            raise ValidationError('Username cannot start with a number or underscore.')

        reserved_usernames = [
            'admin', 'administrator', 'root', 'api', 'www', 'mail', 'ftp',
            'blog', 'user', 'users', 'support', 'help', 'about', 'contact',
            'login', 'register', 'signup', 'signin', 'logout', 'profile',
            'dashboard', 'settings', 'account', 'home', 'index'
        ]
        if username in reserved_usernames:
            raise ValidationError('This username is reserved. Please choose another one.')

        if CustomUser.objects.filter(username=username).exists():
            raise ValidationError('A user with this username already exists.')

        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if CustomUser.objects.filter(email=email).exists():
            raise ValidationError('A user with this email already exists.')
        return email

class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label='Email or Username',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email ',
            'autofocus': True
        })
    )
    
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your password'
        })
    )
    
    remember_me = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )

    def clean(self):
        username_or_email = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if username_or_email and password:
            # Since CustomUser uses email as USERNAME_FIELD, we need to handle both cases
            if '@' in username_or_email:
                # It's an email
                email = username_or_email
            else:
                # It's a username, find the corresponding email
                try:
                    user = CustomUser.objects.get(username=username_or_email.lower())
                    email = user.email
                except CustomUser.DoesNotExist:
                    raise forms.ValidationError("Invalid username or password.")
            
            # Authenticate with email (since that's your USERNAME_FIELD)
            self.user_cache = authenticate(
                self.request,
                username=email,  # Use email for authentication
                password=password
            )
            
            if self.user_cache is None:
                raise forms.ValidationError("Invalid email/username or password.")
            else:
                self.confirm_login_allowed(self.user_cache)

        return self.cleaned_data
