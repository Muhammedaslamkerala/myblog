

from django import forms
from django.contrib.auth import get_user_model
from django_ckeditor_5.widgets import CKEditor5Widget
from .models import Post, Category, Tag
# from comments.models import Comment
from django.core.mail import send_mail
from django.conf import settings
from django.core.files.uploadedfile import UploadedFile 
from .models import Series, Post


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

class PostFilterForm(forms.Form):
    SORT_CHOICES = [
        ('-published_date', 'Newest First'),
        ('published_date', 'Oldest First'),
        ('-views_count', 'Most Viewed'),
        ('-likes_count', 'Most Liked'),
        ('title', 'Title A-Z'),
        ('-title', 'Title Z-A'),
    ]

    category = forms.ModelChoiceField(
        queryset=Category.objects.filter(is_active=True),
        empty_label="All Categories",
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select form-select-sm'
        })
    )
    
    tag = forms.ModelChoiceField(
        queryset=Tag.objects.all(),
        empty_label="All Tags",
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select form-select-sm'
        })
    )
    
    sort_by = forms.ChoiceField(
        choices=SORT_CHOICES,
        initial='-published_date',
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select form-select-sm'
        })
    )
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search posts...'
        })
    )

# class CommentForm(forms.ModelForm):
#     class Meta:
#         model = Comment
#         fields = ['body']
#         widgets = {
#             'body': forms.Textarea(attrs={
#                 'class': 'form-control modern-textarea',
#                 'rows': 4,
#                 'placeholder': 'Write your comment here...',
#                 'style': 'resize: vertical; min-height: 100px;'
#             })
#         }

#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.fields['body'].label = ''





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






class SeriesForm(forms.ModelForm):
    """
    Form for creating and editing a Series.
    Allows the author to select which of their published posts to include.
    """
    
    posts = forms.ModelMultipleChoiceField(
        queryset=Post.objects.none(),  # Will be set in __init__
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Select Posts for this Series",
        help_text="Choose the posts you want to include in this series. You can reorder them after saving."
    )
    
    class Meta:
        model = Series
        fields = ['title', 'description', 'posts']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter series title (e.g., "Python for Beginners")',
                'maxlength': 200
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Describe what readers will learn in this series...',
                'rows': 4
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if self.user:
            # Only show the current user's published posts
            self.fields['posts'].queryset = Post.objects.filter(
                author=self.user,
                status='published'
            ).order_by('-published_date')
            
        # If editing an existing series, pre-select its posts
        if self.instance and self.instance.pk:
            self.fields['posts'].initial = self.instance.posts.all()
    
    def clean_title(self):
        """
        Ensure the title is unique for this author.
        """
        title = self.cleaned_data.get('title')
        
        # Check if another series by this author has the same title
        existing = Series.objects.filter(
            author=self.user,
            title__iexact=title
        )
        
        # If editing, exclude the current instance from the check
        if self.instance and self.instance.pk:
            existing = existing.exclude(pk=self.instance.pk)
        
        if existing.exists():
            raise forms.ValidationError(
                "You already have a series with this title. Please choose a different title."
            )
        
        return title
    
    def save(self, commit=True):
        """
        Save the series and update the posts' series relationship.
        """
        series = super().save(commit=False)
        
        if commit:
            series.save()
            
            # Clear existing posts from this series
            Post.objects.filter(series=series).update(series=None, order_in_series=0)
            
            # Add selected posts to the series with ordering
            selected_posts = self.cleaned_data.get('posts', [])
            for index, post in enumerate(selected_posts, start=1):
                post.series = series
                post.order_in_series = index
                post.save()
        
        return series


class SeriesReorderForm(forms.Form):
    """
    Form for reordering posts within a series via AJAX.
    Expects a list of post IDs in the desired order.
    """
    post_order = forms.CharField(
        widget=forms.HiddenInput(),
        help_text="Comma-separated list of post IDs in order"
    )
    
    def __init__(self, *args, **kwargs):
        self.series = kwargs.pop('series', None)
        super().__init__(*args, **kwargs)
    
    def clean_post_order(self):
        """
        Validate that all post IDs belong to this series.
        """
        post_order = self.cleaned_data.get('post_order', '')
        
        try:
            post_ids = [int(id.strip()) for id in post_order.split(',') if id.strip()]
        except ValueError:
            raise forms.ValidationError("Invalid post ID format")
        
        # Verify all posts belong to this series
        series_post_ids = list(self.series.posts.values_list('id', flat=True))
        
        if set(post_ids) != set(series_post_ids):
            raise forms.ValidationError("Post list doesn't match series posts")
        
        return post_ids
    
    def save(self):
        """
        Update the order_in_series for each post.
        """
        post_ids = self.cleaned_data['post_order']
        
        for index, post_id in enumerate(post_ids, start=1):
            Post.objects.filter(id=post_id).update(order_in_series=index)