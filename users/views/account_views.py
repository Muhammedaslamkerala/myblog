from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import DetailView, UpdateView, TemplateView
from django.urls import reverse
from django.contrib import messages
from ..forms.account_forms import AccountSettingsForm, ProfileEditForm
from ..forms.password_forms import CustomPasswordChangeForm
from ..models.custom_user import CustomUser
from ..models.profile import Profile
from ..models.follow import Follow
from blog.models import Post
from django.contrib.auth import logout
from django.views import View
from ..utils import send_email_change_verification, send_account_update_notification, generate_otp
from ..models.otp import EmailVerificationOTP
from ..forms.account_forms import EmailChangeVerificationForm
import logging

User = CustomUser
logger = logging.getLogger(__name__)


class UserProfileView(DetailView):
    model = User
    template_name = 'users/profile.html'
    context_object_name = 'profile_user'
    
    def get_object(self, queryset=None):
        username = self.kwargs.get('username')
        if username:
            return get_object_or_404(User, username=username, is_active=True)
        if self.request.user.is_authenticated:
            return self.request.user
        return redirect('users:login')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.get_object()
        
        # Ensure profile exists
        Profile.objects.get_or_create(user=user)
        
        # Fetch posts
        posts = Post.objects.filter(author=user)
        published_posts = Post.objects.public().filter(author=user)
        draft_posts = Post.objects.drafts().filter(author=user)
        
        from django.db.models import Sum
        total_views = posts.aggregate(total=Sum('views_count'))['total'] or 0
        total_likes = published_posts.aggregate(total=Sum('likes_count'))['total'] or 0
        
        context.update({
            'total_posts': published_posts.count(),
            'total_drafts': draft_posts.count(),
            'total_views': total_views,
            'total_likes': total_likes,
            'member_since': user.date_joined,
            'is_own_profile': user == self.request.user,
            'followers_count': user.followers_count(),
            'following_count': user.following_count(),
            'is_following': user.is_followed_by(self.request.user) if self.request.user.is_authenticated else False,
            'recent_posts': published_posts.order_by('-created_at')[:5],
            'popular_posts': published_posts.filter(views_count__gt=0).order_by('-views_count')[:3] if published_posts.exists() else [],
        })
        return context


class UserProfileEditView(LoginRequiredMixin, UpdateView):
    """View for editing user profile"""
    model = Profile
    form_class = ProfileEditForm
    template_name = 'users/profile_edit.html'
    
    def get_object(self, queryset=None):
        """Get or create profile for current user"""
        profile, created = Profile.objects.get_or_create(user=self.request.user)
        if created:
            logger.info(f'Created new profile for user: {self.request.user.username}')
        return profile
    
    def get_form_kwargs(self):
        """Pass user instance to form"""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_context_data(self, **kwargs):
        """Add profile to context for easier template access"""
        context = super().get_context_data(**kwargs)
        context['profile'] = self.object
        return context
    
    def get_success_url(self):
        """Redirect to user profile after successful update"""
        return reverse('users:user_profile', kwargs={'username': self.request.user.username})
    
    def form_valid(self, form):
        """Save both profile and user fields"""
        try:
            # Save the profile instance (includes profile_picture)
            profile = form.save(commit=False)
            
            # Update user fields
            user = self.request.user
            user.username = form.cleaned_data.get('username')
            user.first_name = form.cleaned_data.get('first_name', '')
            user.last_name = form.cleaned_data.get('last_name', '')
            user.save()
            
            # Save profile (this will save the profile_picture if uploaded)
            profile.save()
            
            # Log success
            logger.info(f'Profile updated successfully for user: {user.username}')
            
            messages.success(self.request, 'Profile updated successfully!')
            return super().form_valid(form)
            
        except Exception as e:
            logger.error(f'Error updating profile for {self.request.user.username}: {str(e)}')
            messages.error(self.request, f'Error updating profile: {str(e)}')
            return self.form_invalid(form)
            
class AccountSettingsView(LoginRequiredMixin, TemplateView):
    template_name = 'users/account_settings.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Ensure profile exists
        Profile.objects.get_or_create(user=self.request.user)
        
        # Check for pending email change
        pending_otp = EmailVerificationOTP.objects.filter(
            user=self.request.user,
            is_used=False
        ).order_by('-created_at').first()
        
        pending_email = pending_otp.email if pending_otp else None
        
        context['account_form'] = AccountSettingsForm(instance=self.request.user)
        context['password_form'] = CustomPasswordChangeForm(self.request.user)
        context['has_pending_email'] = bool(pending_email)
        context['pending_email'] = pending_email
        
        if pending_email:
            context['email_verify_form'] = EmailChangeVerificationForm(
                self.request.user,
                pending_email
            )
        
        return context
    
    def post(self, request, *args, **kwargs):
        form_type = request.POST.get('form_type')
        
        if form_type == 'account':
            original_email = request.user.email
            form = AccountSettingsForm(request.POST, instance=request.user)
            
            if form.is_valid():
                new_email = form.cleaned_data.get('email')
                email_changed = new_email != original_email
                
                if email_changed:
                    # Generate OTP for email change
                    otp = generate_otp()
                    
                    # Delete existing pending changes
                    EmailVerificationOTP.objects.filter(
                        user=request.user,
                        is_used=False
                    ).delete()
                    
                    # Create new OTP
                    EmailVerificationOTP.objects.create(
                        user=request.user,
                        email=new_email,
                        otp=otp,
                        is_used=False
                    )
                    
                    if send_email_change_verification(request.user, new_email, otp):
                        messages.success(
                            request,
                            f'Verification code sent to {new_email}. Please verify to complete the change.'
                        )
                    else:
                        messages.error(request, 'Failed to send verification email.')
                    
                    # Save other fields except email
                    user = request.user
                    user.first_name = form.cleaned_data.get('first_name', '')
                    user.last_name = form.cleaned_data.get('last_name', '')
                    user.save(update_fields=['first_name', 'last_name'])
                else:
                    # Save all fields
                    user = request.user
                    user.first_name = form.cleaned_data.get('first_name', '')
                    user.last_name = form.cleaned_data.get('last_name', '')
                    user.save(update_fields=['first_name', 'last_name'])
                    
                    messages.success(request, 'Account settings updated successfully!')
            else:
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f'{field.replace("_", " ").title()}: {error}')
        
        elif form_type == 'verify_email':
            pending_otp = EmailVerificationOTP.objects.filter(
                user=request.user,
                is_used=False
            ).order_by('-created_at').first()
            
            if not pending_otp:
                messages.error(request, 'No pending email change found.')
                return redirect('users:account_settings')
            
            form = EmailChangeVerificationForm(
                request.user,
                pending_otp.email,
                request.POST
            )
            
            if form.is_valid():
                if form.verify_and_update_email():
                    messages.success(request, 'Email address updated successfully!')
                    send_account_update_notification(request.user.id, {'email': request.user.email})
                else:
                    messages.error(request, 'Failed to update email.')
            else:
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f'{error}')
        
        elif form_type == 'resend_email_otp':
            pending_otp = EmailVerificationOTP.objects.filter(
                user=request.user,
                is_used=False
            ).order_by('-created_at').first()
            
            if pending_otp:
                new_otp = generate_otp()
                old_email = pending_otp.email
                pending_otp.delete()
                
                EmailVerificationOTP.objects.create(
                    user=request.user,
                    email=old_email,
                    otp=new_otp,
                    is_used=False
                )
                
                if send_email_change_verification(request.user, old_email, new_otp):
                    messages.success(request, f'New verification code sent to {old_email}')
                else:
                    messages.error(request, 'Failed to resend verification code.')
            else:
                messages.error(request, 'No pending email change found.')
        
        elif form_type == 'cancel_email_change':
            deleted_count = EmailVerificationOTP.objects.filter(
                user=request.user,
                is_used=False
            ).delete()[0]
            
            if deleted_count > 0:
                messages.info(request, 'Email change cancelled.')
            else:
                messages.error(request, 'No pending email change found.')
        
        elif form_type == 'password':
            form = CustomPasswordChangeForm(request.user, request.POST)
            
            if form.is_valid():
                form.save()
                from django.contrib.auth import update_session_auth_hash
                update_session_auth_hash(request, form.user)
                messages.success(request, 'Password changed successfully!')
            else:
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f'{field.replace("_", " ").title()}: {error}')
        
        return redirect('users:account_settings')


class AccountDeleteView(LoginRequiredMixin, View):
    def post(self, request):
        user = request.user
        confirm_username = request.POST.get('confirm_username', '').strip()
        
        if confirm_username != user.username:
            messages.error(request, 'Username did not match. Account not deleted.')
            return redirect('users:account_settings')
        
        # Delete related data
        if hasattr(user, 'posts'):
            user.posts.all().delete()
        if hasattr(user, 'comments'):
            user.comments.all().delete()
        
        username = user.username
        user.delete()
        logout(request)
        
        messages.success(request, f"Your account '{username}' has been deleted successfully.")
        return redirect('blog:home')