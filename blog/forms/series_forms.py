
from django import forms
from django.contrib.auth import get_user_model
from django_ckeditor_5.widgets import CKEditor5Widget
from ..models import Post, Series

from django.core.files.uploadedfile import UploadedFile 
from ..models import  Post




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