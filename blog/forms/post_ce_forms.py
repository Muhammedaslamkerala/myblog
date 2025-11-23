
from django import forms
from django.contrib.auth import get_user_model
from django_ckeditor_5.widgets import CKEditor5Widget
from ..models import Post, Category, Tag, Comment
from django.core.mail import send_mail
from django.conf import settings
from django.core.files.uploadedfile import UploadedFile 
from ..models import  Post


User = get_user_model()


class PostForm(forms.ModelForm):
    """
    A unified form for both creating and editing blog posts.
    The status is now controlled by a dropdown field.
    """
    categories = forms.ModelMultipleChoiceField(
        queryset=Category.objects.filter(is_active=True),
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input'
        }),
        required=False
    )
    
    tags_input = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., python, django, web dev',
            'id': 'tags_input'
        }),
        label='Tags',
        help_text='Separate tags with commas.'
    )
    
    featured_image = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={
            'id': 'id_featured_image',
            'accept': 'image/*',
            'style': 'display: none;' # Hidden by default, triggered by the styled div
        })
    )
    
    excerpt = forms.CharField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = Post
        fields = [
            'title', 'body', 'status', 'categories', 
            'featured_image', 'is_featured', 
            'excerpt', 'tags_input'
        ]
        
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'title-input',
                'placeholder': 'Your Awesome Post Title...',
                'id': 'id_title'
            }),
            'body': CKEditor5Widget(config_name='default'),
            'status': forms.Select(attrs={
                'class': 'form-select',
                'id': 'id_status'
            }),
            'is_featured': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'id': 'id_is_featured'
            }),
        }

    def clean_title(self):
        title = self.cleaned_data.get('title', '').strip()
        if len(title) < 5:
            raise forms.ValidationError('Title must be at least 5 characters long.')
        return title

    def clean_tags_input(self):
        tags_input = self.cleaned_data.get('tags_input', '')
        # Standardize to comma-separated values
        return ','.join([t.strip() for t in tags_input.split(',') if t.strip()])

    def clean_featured_image(self):
        image = self.cleaned_data.get('featured_image')
        # This validation runs only when a *new* file is uploaded
        if isinstance(image, UploadedFile):
            if image.size > 10 * 1024 * 1024: # 10MB
                raise forms.ValidationError('Image file size cannot exceed 10MB.')
            if not image.content_type.startswith('image/'):
                raise forms.ValidationError('Only image files are allowed.')
        return image