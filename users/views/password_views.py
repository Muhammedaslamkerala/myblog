import logging
from django.shortcuts import redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import (
    PasswordResetView, PasswordResetDoneView, 
    PasswordResetConfirmView, PasswordResetCompleteView, 
    PasswordChangeView
)
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.messages.views import SuccessMessageMixin
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse_lazy, reverse
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from users.models.notification import EmailNotification
from users.forms import (
    CustomPasswordChangeForm,
    CustomPasswordResetForm,
    CustomSetPasswordForm
)

logger = logging.getLogger(__name__)
User = get_user_model()

class ChangePasswordView(LoginRequiredMixin, PasswordChangeView):
    """Handle password changes for authenticated users"""
    form_class = CustomPasswordChangeForm
    template_name = 'users/password_change.html'

    def get_success_url(self):
        return reverse('users:user_profile', kwargs={'username': self.request.user.username})

    def form_valid(self, form):
        messages.success(self.request, 'Password changed successfully!')
        
        # Send notification
        try:
            notification = EmailNotification.objects.create(
                user=self.request.user,
                notification_type='account_update',
                subject=f'Password Changed - {settings.SITE_NAME or "MyBlog"}',
                content='Your password was recently changed'
            )
            notification.set_context_data({
                'changes_made': 'Password updated',
                'updated_at': notification.created_at.isoformat(),
            })
            notification.save()
            notification.send()
        except Exception as e:
            logger.error(f"Failed to send password change notification: {e}")
        
        return super().form_valid(form)

    def form_invalid(self, form):
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(self.request, f'{field.replace("_", " ").title()}: {error}')
        return super().form_invalid(form)


class CustomPasswordResetView(PasswordResetView):
    template_name = "users/forgot_password.html"
    email_template_name = "emails/password_reset.html"
    subject_template_name = "emails/password_reset_subject.txt"
    success_url = reverse_lazy("users:password_reset_done")

    def form_valid(self, form):
        email = form.cleaned_data["email"]
        users = User.objects.filter(email=email, is_active=True)

        if not users.exists():
            messages.error(self.request, "No active account found with that email address.")
            return redirect("users:password_reset")

        for user in users:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)

            reset_link = self.request.build_absolute_uri(
                reverse_lazy(
                    "users:password_reset_confirm",
                    kwargs={"uidb64": uid, "token": token},
                )
            )

            context = {"user": user, "reset_link": reset_link}

            subject = render_to_string(self.subject_template_name, context).strip()
            html_message = render_to_string(self.email_template_name, context)

            email_msg = EmailMultiAlternatives(subject, html_message, settings.DEFAULT_FROM_EMAIL, [user.email])
            email_msg.attach_alternative(html_message, "text/html")

            try:
                email_msg.send()
                messages.success(self.request, f"Password reset email sent to {user.email}.")
            except Exception as e:
                messages.error(self.request, f"Error sending password reset email: {e}")

        return redirect(self.success_url)

class CustomPasswordResetDoneView(PasswordResetDoneView):
    """Show confirmation after password reset email is sent"""
    template_name = 'users/forgot_password.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form_submitted'] = True
        context['email'] = self.request.session.get('reset_email', '')
        return context


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    """Handle the password reset confirmation"""
    template_name = 'users/password_set.html'
    form_class = CustomSetPasswordForm
    success_url = reverse_lazy('users:password_reset_complete')

    def form_valid(self, form):
        response = super().form_valid(form)
        if hasattr(self, 'user') and self.user:
            logger.info(f'Password reset completed for user: {self.user.username}')
            
            # Send confirmation notification
            try:
                notification = EmailNotification.objects.create(
                    user=self.user,
                    notification_type='account_update',
                    subject=f'Password Reset Successful - {settings.SITE_NAME or "MyBlog"}',
                    content='Your password was successfully reset'
                )
                notification.set_context_data({
                    'changes_made': 'Password reset completed',
                    'updated_at': notification.created_at.isoformat(),
                })
                notification.save()
                notification.send()
            except Exception as e:
                logger.error(f"Failed to send password reset confirmation: {e}")
        
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.method == 'POST' and context.get('form') and context['form'].is_valid():
            context['form_submitted'] = True
        return context


class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    """Show success message after password reset is complete"""
    template_name = 'users/password_reset_confirm.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form_submitted'] = True
        return context