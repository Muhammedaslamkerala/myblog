from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from ..models.comment import Comment


class BaseCommentForm(forms.ModelForm):
    """Base form with shared validation logic"""
    
    def clean_body(self):
        """Validate comment body with spam detection"""
        body = self.cleaned_data.get('body', '').strip()
        
        if not body:
            raise ValidationError(_('Comment cannot be empty.'))
        
        # Check minimum length
        min_length = getattr(self, 'min_length', 10)
        if len(body) < min_length:
            raise ValidationError(
                _(f'Comment must be at least {min_length} characters long.')
            )
        
        # Check maximum length
        max_length = getattr(self, 'max_length', 1000)
        if len(body) > max_length:
            raise ValidationError(
                _(f'Comment cannot exceed {max_length} characters.')
            )
        
        # Basic spam detection
        if self.is_spam(body):
            raise ValidationError(
                _('Your comment appears to contain spam or inappropriate content.')
            )
        
        return body
    
    def is_spam(self, text):
        """Check for spam patterns"""
        spam_patterns = [
            'viagra', 'casino', 'lottery', 'win money', 'click here',
            'buy now', 'limited offer', 'earn money fast', 'work from home',
            'pills', 'pharmaceuticals', 'cheap meds'
        ]
        
        text_lower = text.lower()
        
        # Check for spam words
        for pattern in spam_patterns:
            if pattern in text_lower:
                return True
        
        # Check for excessive links (more than 3 URLs)
        import re
        urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', text)
        if len(urls) > 3:
            return True
        
        # Check for excessive capitalization (more than 50% caps)
        if len(text) > 10:
            caps_ratio = sum(1 for c in text if c.isupper()) / len(text)
            if caps_ratio > 0.5:
                return True
        
        return False


class CommentForm(BaseCommentForm):
    """Main comment form for blog posts"""
    
    min_length = 10
    max_length = 1000
    
    class Meta:
        model = Comment
        fields = ['body']
        widgets = {
            'body': forms.Textarea(attrs={
                'class': 'form-control comment-textarea',
                'rows': 5,
                'placeholder': 'Share your thoughts... (10-1000 characters)',
                'required': True,
                'aria-label': 'Comment text'
            })
        }
    
    def __init__(self, *args, post=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.post = post
        self.user = user
        self.fields['body'].label = ''
        
        # Add character counter attributes
        self.fields['body'].widget.attrs.update({
            'data-max-length': str(self.max_length),
            'data-min-length': str(self.min_length),
        })
    
    def save(self, commit=True):
        """Save comment with post and author"""
        comment = super().save(commit=False)
        
        if self.post:
            comment.post = self.post
        if self.user:
            comment.author = self.user
        
        if commit:
            comment.save()
        
        return comment


class CommentReplyForm(BaseCommentForm):
    """Reply form for nested comments"""
    
    min_length = 5
    max_length = 500
    
    class Meta:
        model = Comment
        fields = ['body']
        widgets = {
            'body': forms.Textarea(attrs={
                'class': 'form-control reply-textarea',
                'rows': 3,
                'placeholder': 'Write your reply... (5-500 characters)',
                'required': True,
                'aria-label': 'Reply text'
            })
        }
    
    def __init__(self, *args, parent=None, post=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.parent = parent
        self.post = post
        self.user = user
        self.fields['body'].label = ''
        
        # Add character counter attributes
        self.fields['body'].widget.attrs.update({
            'data-max-length': str(self.max_length),
            'data-min-length': str(self.min_length),
        })
    
    def clean(self):
        """Additional validation for replies"""
        cleaned_data = super().clean()
        
        # Validate parent exists and is not deleted/unapproved
        if self.parent:
            if not self.parent.is_approved:
                raise ValidationError(
                    _('Cannot reply to an unapproved comment.')
                )
            
            # Check nesting depth
            depth = 0
            current = self.parent
            max_depth = 3
            
            while current and depth < max_depth:
                depth += 1
                current = current.parent
            
            if depth >= max_depth:
                raise ValidationError(
                    _('Reply nesting is too deep. Maximum depth is 3.')
                )
        
        return cleaned_data
    
    def save(self, commit=True):
        """Save reply with parent, post and author"""
        reply = super().save(commit=False)
        
        if self.parent:
            reply.parent = self.parent
            reply.post = self.parent.post  # Inherit post from parent
        elif self.post:
            reply.post = self.post
        
        if self.user:
            reply.author = self.user
        
        if commit:
            reply.save()
        
        return reply


class CommentEditForm(BaseCommentForm):
    """Form for editing existing comments"""
    
    min_length = 10
    max_length = 1000
    
    class Meta:
        model = Comment
        fields = ['body']
        widgets = {
            'body': forms.Textarea(attrs={
                'class': 'form-control comment-textarea',
                'rows': 5,
                'required': True,
                'aria-label': 'Edit comment'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['body'].label = ''
        
        # Adjust max length for replies
        if self.instance and self.instance.is_reply:
            self.max_length = 500
        
        # Add character counter attributes
        self.fields['body'].widget.attrs.update({
            'data-max-length': str(self.max_length),
            'data-min-length': str(self.min_length),
        })
    
    def clean(self):
        """Additional validation for editing"""
        cleaned_data = super().clean()
        
        # Check if user is allowed to edit (optional - handle in view)
        if self.instance and self.instance.pk:
            # You might want to check time limits for editing
            from django.utils import timezone
            from datetime import timedelta
            
            edit_window = timedelta(minutes=30)  # 30 minute edit window
            time_since_published = timezone.now() - self.instance.published_date
            
            if time_since_published > edit_window:
                # Just a warning - enforce in view if needed
                pass
        
        return cleaned_data


class CommentModerationForm(forms.ModelForm):
    """Admin form for moderating comments"""
    
    class Meta:
        model = Comment
        fields = ['is_approved', 'is_flagged', 'flagged_reason']
        widgets = {
            'flagged_reason': forms.Textarea(attrs={
                'rows': 2,
                'class': 'form-control'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['is_approved'].widget.attrs.update({'class': 'form-check-input'})
        self.fields['is_flagged'].widget.attrs.update({'class': 'form-check-input'})


class CommentFilterForm(forms.Form):
    """Form for filtering comments in admin/views"""
    
    STATUS_CHOICES = [
        ('', 'All Comments'),
        ('approved', 'Approved'),
        ('pending', 'Pending Approval'),
        ('flagged', 'Flagged'),
    ]
    
    SORT_CHOICES = [
        ('-published_date', 'Newest First'),
        ('published_date', 'Oldest First'),
        ('-updated_at', 'Recently Updated'),
    ]
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    sort = forms.ChoiceField(
        choices=SORT_CHOICES,
        required=False,
        initial='-published_date',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search comments...'
        })
    )