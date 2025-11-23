from django import forms
from ..models import Post, Category, Tag



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
