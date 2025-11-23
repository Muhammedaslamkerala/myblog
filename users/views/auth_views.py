# users/views/auth_views.py

import logging
from django.shortcuts import redirect, render
from django.views import View
from django.contrib.auth.views import LoginView
from django.contrib.auth import login, logout
from django.urls import reverse_lazy
from django.contrib import messages
from django.utils import timezone
from django.core.signing import Signer, BadSignature
from ..forms.auth_forms import LoginForm, RegistrationForm
from ..models import CustomUser, EmailVerificationOTP
from ..utils import generate_otp, send_otp_email

logger = logging.getLogger(__name__)


class RegistrationView(View):
    template_name = 'users/signup.html'
    form_class = RegistrationForm
    
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('blog:home')
        form = self.form_class()
        return render(request, self.template_name, {'form': form})
    
    def post(self, request):
        form = self.form_class(request.POST)
        
        if form.is_valid():
            try:
                # Extract form data
                email = form.cleaned_data['email']
                password = form.cleaned_data['password1']
                first_name = form.cleaned_data.get('first_name', '')
                last_name = form.cleaned_data.get('last_name', '')
                username = form.cleaned_data.get('username', '')
                
                # Check if email already exists
                if CustomUser.objects.filter(email=email).exists():
                    messages.error(request, 'An account with this email already exists.')
                    return render(request, self.template_name, {'form': form})
                
                # Generate OTP
                otp = generate_otp()
                
                logger.info(f"OTP generated for registration: {email}")
                
                # Store registration data in session
                signer = Signer()
                registration_data = {
                    'email': email,
                    'password': password,
                    'first_name': first_name,
                    'last_name': last_name,
                    'username': username,
                    'otp': otp,
                    'otp_created_at': timezone.now().isoformat(),
                    'attempts': 0
                }
                
                request.session['pending_registration'] = signer.sign_object(registration_data)
                
                # Send OTP email (using temp user object for display purposes)
                temp_user = CustomUser(email=email, first_name=first_name)
                
                if send_otp_email(temp_user, otp):
                    messages.success(
                        request, 
                        'Please check your email for the verification code to complete registration.'
                    )
                    return redirect('users:verify_email')
                else:
                    logger.error(f"Failed to send OTP email to {email}")
                    messages.error(
                        request, 
                        'Failed to send verification email. Please try again or contact support.'
                    )
                    if 'pending_registration' in request.session:
                        del request.session['pending_registration']
                    
            except Exception as e:
                logger.exception(f"Registration error: {e}")
                messages.error(request, 'Registration failed due to an unexpected error. Please try again.')
        
        return render(request, self.template_name, {'form': form})


class VerifyEmailView(View):
    template_name = 'users/verify_email.html'
    
    def get(self, request):
        # Check for pending registration
        if 'pending_registration' in request.session:
            try:
                signer = Signer()
                registration_data = signer.unsign_object(request.session['pending_registration'])
                return render(request, self.template_name, {'email': registration_data['email']})
            except (BadSignature, KeyError):
                messages.error(request, 'Invalid verification session. Please register again.')
                if 'pending_registration' in request.session:
                    del request.session['pending_registration']
                return redirect('users:signup')
        
        messages.error(request, 'No pending verification found. Please register first.')
        return redirect('users:signup')
    
    def post(self, request):
        otp_input = request.POST.get('otp', '').strip()
        
        if not otp_input:
            messages.error(request, 'Please enter the verification code.')
            return self.get(request)
        
        # Validate OTP format
        if not otp_input.isdigit() or len(otp_input) != 6:
            messages.error(request, 'Verification code must be 6 digits.')
            return self.get(request)
        
        if 'pending_registration' not in request.session:
            messages.error(request, 'No pending verification found.')
            return redirect('users:signup')
        
        try:
            signer = Signer()
            registration_data = signer.unsign_object(request.session['pending_registration'])
            
            # Check OTP expiry (10 minutes)
            otp_created_at = timezone.datetime.fromisoformat(registration_data['otp_created_at'])
            if timezone.now() > otp_created_at + timezone.timedelta(minutes=10):
                messages.error(request, 'Verification code has expired. Please register again.')
                del request.session['pending_registration']
                return redirect('users:signup')
            
            # Check attempts
            if registration_data['attempts'] >= 3:
                messages.error(request, 'Too many failed attempts. Please register again.')
                del request.session['pending_registration']
                return redirect('users:signup')
            
            # Verify OTP
            if registration_data['otp'] == otp_input:
                # Create the user after successful verification
                user = CustomUser(
                    email=registration_data['email'],
                    first_name=registration_data['first_name'],
                    last_name=registration_data['last_name'],
                    username=registration_data['username'],
                    is_active=True,
                    email_verified=True,
                    email_verified_at=timezone.now()
                )
                
                # Generate username if not provided
                if not user.username:
                    base_username = user.email.split('@')[0].lower()
                    username = base_username
                    counter = 1
                    while CustomUser.objects.filter(username=username).exists():
                        username = f"{base_username}{counter}"
                        counter += 1
                    user.username = username
                
                # Set password
                user.set_password(registration_data['password'])
                user.save()
                
                logger.info(f"New user created: {user.username} ({user.email})")
                
                # Clear session
                del request.session['pending_registration']
                
                # Log user in
                login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                
                # Send welcome email (non-blocking)
                try:
                    from ..utils import send_welcome_email
                    send_welcome_email(user.id)
                except Exception as e:
                    logger.error(f"Failed to send welcome email to {user.email}: {e}")
                
                messages.success(
                    request, 
                    f'Registration successful! Welcome to MyBlog, {user.first_name or user.username}!'
                )
                return redirect('blog:home')
            else:
                # Increment attempts
                registration_data['attempts'] += 1
                request.session['pending_registration'] = signer.sign_object(registration_data)
                request.session.modified = True
                
                remaining = 3 - registration_data['attempts']
                if remaining > 0:
                    messages.error(request, f'Invalid verification code. You have {remaining} attempt(s) remaining.')
                else:
                    messages.error(request, 'Invalid verification code. No attempts remaining. Please register again.')
                    del request.session['pending_registration']
                    return redirect('users:signup')
                
                return render(request, self.template_name, {'email': registration_data['email']})
                
        except (BadSignature, KeyError) as e:
            logger.error(f"Session data error: {e}")
            messages.error(request, 'Invalid verification session. Please register again.')
            if 'pending_registration' in request.session:
                del request.session['pending_registration']
            return redirect('users:signup')
        except Exception as e:
            logger.exception(f"Verification error: {e}")
            messages.error(request, 'Verification failed due to an unexpected error. Please try again.')
            return redirect('users:signup')


class ResendOTPView(View):
    def post(self, request):
        if 'pending_registration' not in request.session:
            messages.error(request, 'No pending verification found.')
            return redirect('users:signup')
        
        try:
            signer = Signer()
            registration_data = signer.unsign_object(request.session['pending_registration'])
            
            # Check rate limiting (1 minute)
            otp_created_at = timezone.datetime.fromisoformat(registration_data['otp_created_at'])
            if timezone.now() < otp_created_at + timezone.timedelta(minutes=1):
                messages.error(request, 'Please wait at least 1 minute before requesting a new code.')
                return redirect('users:verify_email')
            
            # Generate new OTP
            otp = generate_otp()
            registration_data['otp'] = otp
            registration_data['otp_created_at'] = timezone.now().isoformat()
            registration_data['attempts'] = 0
            
            request.session['pending_registration'] = signer.sign_object(registration_data)
            request.session.modified = True
            
            logger.info(f"New OTP generated for: {registration_data['email']}")
            
            # Send OTP email
            temp_user = CustomUser(email=registration_data['email'], first_name=registration_data['first_name'])
            
            if send_otp_email(temp_user, otp):
                messages.success(request, 'A new verification code has been sent to your email.')
            else:
                messages.error(request, 'Failed to send verification code. Please try again or contact support.')
            
            return redirect('users:verify_email')
            
        except (BadSignature, KeyError) as e:
            logger.error(f"Session data error: {e}")
            messages.error(request, 'Invalid verification session. Please register again.')
            if 'pending_registration' in request.session:
                del request.session['pending_registration']
            return redirect('users:signup')
        except Exception as e:
            logger.exception(f"Resend OTP error: {e}")
            messages.error(request, 'Failed to resend verification code. Please try again.')
            return redirect('users:verify_email')


class CustomLoginView(LoginView):
    template_name = 'users/login.html'
    form_class = LoginForm
    redirect_authenticated_user = True
    
    def get_success_url(self):
        next_page = self.request.GET.get('next')
        if next_page:
            return next_page
        return reverse_lazy('blog:home')

    def form_valid(self, form):
        remember_me = form.cleaned_data.get('remember_me', False)
        
        if not remember_me:
            self.request.session.set_expiry(0)
        else:
            self.request.session.set_expiry(30 * 24 * 60 * 60)
        
        user = form.get_user()
        
        # Check if email is verified
        if not user.email_verified:
            messages.warning(
                self.request,
                'Please verify your email address before logging in. Check your inbox for the verification code.'
            )
            self.request.session['pending_user_id'] = user.id
            
            # Generate and send new OTP
            try:
                otp = generate_otp()
                EmailVerificationOTP.objects.create(user=user, otp=otp)
                send_otp_email(user, otp)
            except Exception as e:
                logger.error(f"Failed to send OTP to unverified user {user.email}: {e}")
            
            return redirect('users:verify_email')
        
        login(self.request, user)
        logger.info(f"User logged in: {user.username} ({user.email})")
        
        messages.success(
            self.request, 
            f'Welcome back, {user.get_display_name()}!'
        )
        
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(
            self.request, 
            'Invalid email or password. Please check your credentials and try again.'
        )
        return super().form_invalid(form)


class LogoutUserView(View):
    def get(self, request):
        if request.user.is_authenticated:
            username = request.user.get_display_name()
            logout(request)
            messages.success(request, f'Goodbye, {username}! You have been successfully logged out.')
        else:
            logout(request)
            messages.info(request, 'You have been logged out.')
        return redirect('blog:home')

    def post(self, request):
        return self.get(request)