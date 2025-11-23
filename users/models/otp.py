from django.db import models
from django.utils import timezone
from datetime import timedelta

class EmailVerificationOTP(models.Model):
    """Model to store email verification OTPs"""
    user = models.ForeignKey(
        'CustomUser',
        on_delete=models.CASCADE,
        related_name='verification_otps'
    )
    email = models.EmailField(null=True, blank=True)
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    attempts = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Email Verification OTP'
        verbose_name_plural = 'Email Verification OTPs'
    
    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(minutes=10)
        super().save(*args, **kwargs)
    
    def is_valid(self):
        """Check if OTP is still valid"""
        return (
            not self.is_used and 
            timezone.now() < self.expires_at and 
            self.attempts < 3
        )
    
    def __str__(self):
        return f"OTP for {self.user.email} - {'Valid' if self.is_valid() else 'Invalid'}"