import imghdr
from django import forms
from django.core.exceptions import ValidationError
from ..models.custom_user import CustomUser
from ..models.profile import Profile
from datetime import timedelta
from django.utils import timezone
from ..models.otp import EmailVerificationOTP
import re

class ProfileEditForm(forms.ModelForm):
    """Form for editing user profile information"""
    
    # User fields (not in Profile model)
    username = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Username'
        }),
        help_text='30 characters or fewer. Letters, numbers and underscores only.'
    )
    
    first_name = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'First name'
        })
    )
    
    last_name = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Last name'
        })
    )

    class Meta:
        model = Profile
        fields = [
            'bio', 'profile_picture', 'website',
            'twitter_url', 'linkedin_url', 'github_url'
        ]
        widgets = {
            'bio': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Tell us about yourself...'
            }),
            'profile_picture': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'website': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://your-website.com'
            }),
            'twitter_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://twitter.com/username'
            }),
            'linkedin_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://linkedin.com/in/username'
            }),
            'github_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://github.com/username'
            }),
        }
        help_texts = {
            'bio': 'Optional. Write a brief description about yourself.',
            'profile_picture': 'Optional. Upload a profile picture (JPG, PNG, max 5MB).',
            'website': 'Optional. Your personal website or portfolio.',
            'twitter_url': 'Optional. Your Twitter/X profile URL.',
            'linkedin_url': 'Optional. Your LinkedIn profile URL.',
            'github_url': 'Optional. Your GitHub profile URL.',
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Pre-populate user fields if user is provided
        if self.user:
            self.fields['username'].initial = self.user.username
            self.fields['first_name'].initial = self.user.first_name
            self.fields['last_name'].initial = self.user.last_name

    def clean_username(self):
        """Validate username"""
        username = self.cleaned_data.get('username')
        
        if not username:
            raise ValidationError('Username is required.')
        
        username = username.lower()
        
        # Allow current user's username
        if self.user and self.user.username == username:
            return username
        
        # Validation rules
        if len(username) < 3:
            raise ValidationError('Username must be at least 3 characters long.')
        
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            raise ValidationError('Username can only contain letters, numbers, and underscores.')
        
        if username[0].isdigit() or username[0] == '_':
            raise ValidationError('Username cannot start with a number or underscore.')
        
        if CustomUser.objects.filter(username=username).exists():
            raise ValidationError('A user with this username already exists.')
        
        return username

    def clean_profile_picture(self):
        """Validate profile picture"""
        profile_picture = self.cleaned_data.get('profile_picture')
        
        if profile_picture:
            # Check if it's a new upload (has 'size' attribute)
            if hasattr(profile_picture, 'size'):
                # Check file size (5MB limit)
                if profile_picture.size > 5 * 1024 * 1024:
                    raise ValidationError('Image file too large ( > 5MB )')
                
                # Check file type
                try:
                    file_type = profile_picture.content_type
                    if not file_type.startswith('image/'):
                        raise ValidationError('Invalid file type. Please upload an image.')
                except AttributeError:
                    pass
                
                # Extra validation using imghdr
                try:
                    image_type = imghdr.what(profile_picture)
                    if image_type not in ['jpeg', 'jpg', 'png', 'gif', 'webp']:
                        raise ValidationError('Invalid image format. Supported: JPG, PNG, GIF, WebP')
                except Exception:
                    raise ValidationError('Invalid image file.')
        
        return profile_picture

    def clean_twitter_url(self):
        """Validate Twitter URL"""
        twitter_url = self.cleaned_data.get('twitter_url')
        if twitter_url:
            if not ('twitter.com' in twitter_url or 'x.com' in twitter_url):
                raise ValidationError('Please enter a valid Twitter/X URL.')
        return twitter_url

    def clean_linkedin_url(self):
        """Validate LinkedIn URL"""
        linkedin_url = self.cleaned_data.get('linkedin_url')
        if linkedin_url:
            if 'linkedin.com' not in linkedin_url:
                raise ValidationError('Please enter a valid LinkedIn URL.')
        return linkedin_url

    def clean_github_url(self):
        """Validate GitHub URL"""
        github_url = self.cleaned_data.get('github_url')
        if github_url:
            if 'github.com' not in github_url:
                raise ValidationError('Please enter a valid GitHub URL.')
        return github_url

    def save(self, commit=True):
        """Save profile instance"""
        profile = super().save(commit=False)
        
        if commit:
            profile.save()
        
        return profile

class AccountSettingsForm(forms.ModelForm):
    """Form for basic account settings (name and email)"""
    
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'First name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Last name'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Email address'
            })
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        
        # If email hasn't changed, return it
        if self.instance and self.instance.email == email:
            return email
        
        # Check if email is already taken by another user
        if CustomUser.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise ValidationError('A user with this email already exists.')

        return email


class EmailChangeVerificationForm(forms.Form):
    """Form for verifying email change with OTP"""
    
    otp = forms.CharField(
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter 6-digit OTP',
            'maxlength': '6',
            'pattern': '[0-9]{6}',
            'inputmode': 'numeric'
        }),
        help_text='Enter the 6-digit code sent to your new email address'
    )

    def __init__(self, user, new_email, *args, **kwargs):
        self.user = user
        self.new_email = new_email
        super().__init__(*args, **kwargs)

    def clean_otp(self):
        otp = self.cleaned_data.get('otp')
        
        if not self.new_email:
            raise ValidationError('No pending email change found.')
        
        # Get the OTP record for this email change
        try:
            otp_record = EmailVerificationOTP.objects.get(
                user=self.user,
                email=self.new_email,
                otp=otp,
                is_used=False
            )
        except EmailVerificationOTP.DoesNotExist:
            raise ValidationError('Invalid OTP. Please try again.')
        
        # Check if OTP has expired (15 minutes)
        expiry_time = otp_record.created_at + timedelta(minutes=15)
        if timezone.now() > expiry_time:
            raise ValidationError('OTP has expired. Please request a new one.')
        
        # Store OTP record for later use
        self.otp_record = otp_record
        
        return otp

    def verify_and_update_email(self):
        """Verify OTP and update email"""
        if not hasattr(self, 'otp_record'):
            return False

        try:
            # Update user email
            self.user.email = self.new_email
            self.user.save(update_fields=['email'])
            
            # Mark OTP as used
            self.otp_record.is_used = True
            self.otp_record.save(update_fields=['is_used'])
            
            return True

        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Error updating email: {e}")
            return False


class NotificationPreferencesForm(forms.ModelForm):
    """Form for notification preferences"""
    
    class Meta:
        model = CustomUser
        fields = ['email_notifications']
        widgets = {
            'email_notifications': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }