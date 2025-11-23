from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    # Authentication URLs
    path('signup/', views.RegistrationView.as_view(), name='signup'),
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.LogoutUserView.as_view(), name='logout'),
    path('verify-email/', views.VerifyEmailView.as_view(), name='verify_email'),
    path('resend-otp/', views.ResendOTPView.as_view(), name='resend_otp'),
    
    # Profile URLs (order matters - more specific first)
    path('profile/edit/', views.UserProfileEditView.as_view(), name='profile_edit'),
    path('profile/', views.UserProfileView.as_view(), name='profile'),
    path('profile/<str:username>/', views.UserProfileView.as_view(), name='user_profile'),

    
    # Follow System
    path("follow/<int:user_id>/", views.toggle_follow, name="toggle_follow"),

    path('api/toggle-follow/', views.api_toggle_follow, name='api_toggle_follow'),
    path('api/users/<int:user_id>/followers/', views.get_user_list, {'list_type': 'followers'}, name='api_get_followers'),
    path('api/users/<int:user_id>/following/', views.get_user_list, {'list_type': 'following'}, name='api_get_following'),

    
    # Password Reset URLs
    path('password-reset/', 
         views.CustomPasswordResetView.as_view(), 
         name='password_reset'),
    path('password-reset/done/', 
         views.CustomPasswordResetDoneView.as_view(), 
         name='password_reset_done'),
    path('password-reset/confirm/<uidb64>/<token>/', 
         views.CustomPasswordResetConfirmView.as_view(), 
         name='password_reset_confirm'),
    path('password-reset/complete/', 
         views.CustomPasswordResetCompleteView.as_view(), 
         name='password_reset_complete'),
    
    # Account Management
    path('settings/', views.AccountSettingsView.as_view(), name='account_settings'),
    path('account-delete/', views.AccountDeleteView.as_view(), name='account_delete'),
    path('password/change/', views.ChangePasswordView.as_view(), name='change_password'),
    
    # AJAX Endpoints
    path('api/upload-profile-picture/', views.upload_profile_picture, name='upload_profile_picture'),
    path('api/remove-profile-picture/', views.remove_profile_picture, name='remove_profile_picture'),
    path('api/check-email/', views.check_email_availability, name='check_email'),
    path('api/check-username/', views.check_username_availability, name='check_username'),


    
    # Notification URLs
    path('notifications/', views.notification_center, name='notification_center'),
    path('notifications/preferences/', views.notification_preferences, name='notification_preferences'),
    path('api/resend-notification/<int:notification_id>/', views.resend_notification, name='resend_notification'),


]