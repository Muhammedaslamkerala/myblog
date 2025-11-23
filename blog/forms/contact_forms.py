from django import forms
from django.core.mail import send_mail
from django.conf import settings


class ContactForm(forms.Form):
    SUBJECT_CHOICES = [
        ('', 'Choose a subject...'),
        ('general', 'General Inquiry'),
        ('support', 'Technical Support'),
        ('partnership', 'Partnership'),
        ('feedback', 'Feedback'),
        ('content', 'Content Issues'),
        ('other', 'Other'),
    ]
    
    first_name = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your first name'
        })
    )
    
    last_name = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your last name'
        })
    )
    
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email address'
        })
    )
    
    subject = forms.ChoiceField(
        choices=SUBJECT_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    
    message = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 6,
            'placeholder': 'Write your message here...'
        })
    )
    
    subscribe_newsletter = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    def send_email(self):
        """Send the contact form email"""
        subject = f"Contact Form: {self.cleaned_data['subject'].title()}"
        message = f"""
        New contact form submission from MyBlog:
        
        Name: {self.cleaned_data['first_name']} {self.cleaned_data['last_name']}
        Email: {self.cleaned_data['email']}
        Subject: {self.cleaned_data['subject']}
        Newsletter Subscription: {'Yes' if self.cleaned_data['subscribe_newsletter'] else 'No'}
        
        Message:
        {self.cleaned_data['message']}
        """
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [settings.CONTACT_EMAIL],  # You'll need to add this to settings
            fail_silently=False,
        )
