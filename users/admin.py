from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils import timezone
from .models.custom_user import CustomUser
from .models.profile import Profile
from .models.follow import Follow
from .models.otp import EmailVerificationOTP
from .models.notification import EmailNotification, LoginLog


class ProfileInline(admin.StackedInline):
    """Inline admin for Profile to show within CustomUser admin"""
    model = Profile
    can_delete = False
    verbose_name_plural = 'Profile Information'
    
    fieldsets = (
        ('Bio & Picture', {
            'fields': ('bio', 'profile_picture', 'profile_picture_preview')
        }),
        ('Contact & Links', {
            'fields': ('website', 'twitter_url', 'linkedin_url', 'github_url')
        }),
        ('AI & Preferences', {
            'fields': ('interests', 'ai_preferences'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('updated_at',),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('profile_picture_preview', 'updated_at')
    
    def profile_picture_preview(self, obj):
        """Show profile picture preview"""
        if obj.profile_picture:
            return format_html(
                '<img src="{}" style="max-width: 150px; max-height: 150px; border-radius: 10px;" />',
                obj.profile_picture.url
            )
        return "No image uploaded"
    profile_picture_preview.short_description = 'Current Picture'


class FollowInline(admin.TabularInline):
    """Show followers in user admin"""
    model = Follow
    fk_name = 'following'
    extra = 0
    readonly_fields = ('follower', 'created_at')
    can_delete = True
    verbose_name = 'Follower'
    verbose_name_plural = 'Recent Followers (showing users who follow this user)'
    
    def has_add_permission(self, request, obj=None):
        return False


class EmailVerificationOTPInline(admin.TabularInline):
    """Show pending email verifications"""
    model = EmailVerificationOTP
    extra = 0
    readonly_fields = ('email', 'otp', 'created_at', 'expires_at', 'is_used', 'attempts')
    fields = ('email', 'otp', 'is_used', 'attempts', 'created_at', 'expires_at')
    can_delete = True
    verbose_name = 'Email Verification OTP'
    verbose_name_plural = 'Email Verification OTPs'
    
    def has_add_permission(self, request, obj=None):
        return False


class LoginLogInline(admin.TabularInline):
    """Show recent login logs"""
    model = LoginLog
    extra = 0
    readonly_fields = ('login_time', 'ip_address', 'user_agent', 'location', 'is_suspicious', 'notification_sent')
    fields = ('login_time', 'ip_address', 'location', 'is_suspicious', 'notification_sent')
    can_delete = False
    verbose_name = 'Login Log'
    verbose_name_plural = 'Recent Login History (Last 10)'
    max_num = 10  # Limit to 10 entries
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(CustomUser)
class CustomUserAdmin(BaseUserAdmin):
    """Enhanced admin interface for CustomUser"""
    
    # Inline models - temporarily removed LoginLogInline
    inlines = [ProfileInline, FollowInline, EmailVerificationOTPInline]
    
    # List display
    list_display = (
        'username_with_avatar',
        'email',
        'full_name',
        'is_active',
        'is_staff',
        'email_verified_badge',
        'followers_count',
        'following_count',
        'last_login_info',
        'date_joined',
        'view_profile_link'
    )
    
    list_display_links = ('username_with_avatar', 'email')
    
    # Filters
    list_filter = (
        'is_active',
        'is_staff',
        'is_superuser',
        'email_verified',
        'email_notifications',
        'date_joined',
        'last_login'
    )
    
    # Search
    search_fields = (
        'username',
        'email',
        'first_name',
        'last_name'
    )
    
    # Ordering
    ordering = ('-date_joined',)
    
    # Field organization
    fieldsets = (
        ('Authentication', {
            'fields': ('username', 'email', 'password')
        }),
        ('Personal Information', {
            'fields': ('first_name', 'last_name')
        }),
        ('Email Verification', {
            'fields': ('email_verified', 'email_verified_at'),
            'classes': ('collapse',)
        }),
        ('Preferences', {
            'fields': ('email_notifications',)
        }),
        ('Permissions', {
            'fields': (
                'is_active',
                'is_staff',
                'is_superuser',
                'groups',
                'user_permissions'
            ),
            'classes': ('collapse',)
        }),
        ('Important Dates', {
            'fields': ('last_login', 'date_joined'),
            'classes': ('collapse',)
        }),
        ('Recent Login Activity', {
            'fields': ('recent_logins_display',),
            'classes': ('collapse',)
        }),
    )
    
    # Add user fieldsets
    add_fieldsets = (
        ('Required Information', {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2'),
        }),
        ('Optional Information', {
            'classes': ('wide',),
            'fields': ('first_name', 'last_name'),
        }),
        ('Permissions', {
            'classes': ('wide',),
            'fields': ('is_active', 'is_staff', 'is_superuser'),
        }),
    )
    
    readonly_fields = ('date_joined', 'last_login', 'email_verified_at', 'recent_logins_display')
    
    # Custom display methods
    def username_with_avatar(self, obj):
        """Display username with avatar"""
        if hasattr(obj, 'profile') and obj.profile.profile_picture:
            return format_html(
                '<div style="display: flex; align-items: center; gap: 10px;">'
                '<img src="{}" style="width: 40px; height: 40px; border-radius: 50%; object-fit: cover;" />'
                '<strong>{}</strong>'
                '</div>',
                obj.profile.profile_picture.url,
                obj.username
            )
        return format_html(
            '<div style="display: flex; align-items: center; gap: 10px;">'
            '<div style="width: 40px; height: 40px; border-radius: 50%; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); '
            'display: flex; align-items: center; justify-content: center; color: white; font-weight: bold;">{}</div>'
            '<strong>{}</strong>'
            '</div>',
            obj.username[0].upper() if obj.username else '?',
            obj.username
        )
    username_with_avatar.short_description = 'Username'
    
    def full_name(self, obj):
        """Display full name"""
        name = obj.get_full_name()
        return name if name else format_html('<em style="color: #999;">Not set</em>')
    full_name.short_description = 'Full Name'
    
    def email_verified_badge(self, obj):
        """Show email verification status as badge"""
        if obj.email_verified:
            return format_html(
                '<span style="background: #10b981; color: white; padding: 3px 8px; '
                'border-radius: 6px; font-size: 11px; font-weight: bold;">✓ VERIFIED</span>'
            )
        return format_html(
            '<span style="background: #ef4444; color: white; padding: 3px 8px; '
            'border-radius: 6px; font-size: 11px; font-weight: bold;">✗ NOT VERIFIED</span>'
        )
    email_verified_badge.short_description = 'Email Status'
    
    def followers_count(self, obj):
        """Display followers count"""
        count = obj.followers_count()
        return format_html(
            '<span style="background: #667eea; color: white; padding: 3px 10px; '
            'border-radius: 6px; font-size: 11px; font-weight: bold;">{} Followers</span>',
            count
        )
    followers_count.short_description = 'Followers'
    
    def following_count(self, obj):
        """Display following count"""
        count = obj.following_count()
        return format_html(
            '<span style="background: #764ba2; color: white; padding: 3px 10px; '
            'border-radius: 6px; font-size: 11px; font-weight: bold;">{} Following</span>',
            count
        )
    following_count.short_description = 'Following'
    
    def last_login_info(self, obj):
        """Show last login with recency indicator"""
        if not obj.last_login:
            return format_html('<span style="color: #999;">Never</span>')
        
        from django.utils.timesince import timesince
        time_ago = timesince(obj.last_login)
        
        # Color code based on recency
        if (timezone.now() - obj.last_login).days < 1:
            color = '#10b981'  # Green - active today
        elif (timezone.now() - obj.last_login).days < 7:
            color = '#f59e0b'  # Orange - active this week
        else:
            color = '#ef4444'  # Red - inactive
        
        return format_html(
            '<span style="color: {}; font-weight: 500;">{} ago</span>',
            color,
            time_ago.split(',')[0]  # Show only the most significant unit
        )
    last_login_info.short_description = 'Last Login'
    
    def view_profile_link(self, obj):
        """Link to view user profile on site"""
        if obj.username:
            url = reverse('users:user_profile', kwargs={'username': obj.username})
            return format_html(
                '<a href="{}" target="_blank" style="color: #667eea; text-decoration: none; font-weight: bold;">'
                '👁 View Profile</a>',
                url
            )
        return '-'
    view_profile_link.short_description = 'Actions'
    
    def recent_logins_display(self, obj):
        """Display recent login logs in a table"""
        if not obj.pk:
            return '-'
        
        logs = LoginLog.objects.filter(user=obj).order_by('-login_time')[:10]
        
        if not logs:
            return format_html('<em style="color: #999;">No login history</em>')
        
        html = '<table style="width: 100%; border-collapse: collapse;">'
        html += '<thead><tr style="background: #f3f4f6;">'
        html += '<th style="padding: 8px; text-align: left; border-bottom: 2px solid #e5e7eb;">Time</th>'
        html += '<th style="padding: 8px; text-align: left; border-bottom: 2px solid #e5e7eb;">IP Address</th>'
        html += '<th style="padding: 8px; text-align: left; border-bottom: 2px solid #e5e7eb;">Location</th>'
        html += '<th style="padding: 8px; text-align: left; border-bottom: 2px solid #e5e7eb;">Status</th>'
        html += '</tr></thead><tbody>'
        
        for log in logs:
            suspicious_badge = ''
            if log.is_suspicious:
                suspicious_badge = '<span style="background: #ef4444; color: white; padding: 2px 6px; border-radius: 4px; font-size: 10px;">⚠️ SUSPICIOUS</span>'
            else:
                suspicious_badge = '<span style="background: #10b981; color: white; padding: 2px 6px; border-radius: 4px; font-size: 10px;">✓ SAFE</span>'
            
            html += f'<tr style="border-bottom: 1px solid #e5e7eb;">'
            html += f'<td style="padding: 8px;">{log.login_time.strftime("%Y-%m-%d %H:%M")}</td>'
            html += f'<td style="padding: 8px;"><code>{log.ip_address}</code></td>'
            html += f'<td style="padding: 8px;">{log.location or "Unknown"}</td>'
            html += f'<td style="padding: 8px;">{suspicious_badge}</td>'
            html += '</tr>'
        
        html += '</tbody></table>'
        
        return format_html(html)
    recent_logins_display.short_description = 'Recent Login History (Last 10)'
    
    # Custom actions
    actions = ['verify_emails', 'deactivate_users', 'activate_users', 'send_welcome_email']
    
    def verify_emails(self, request, queryset):
        """Bulk verify email addresses"""
        count = queryset.update(
            email_verified=True,
            email_verified_at=timezone.now()
        )
        self.message_user(request, f'{count} user(s) email verified successfully.')
    verify_emails.short_description = 'Verify selected users\' emails'
    
    def deactivate_users(self, request, queryset):
        """Bulk deactivate users"""
        count = queryset.update(is_active=False)
        self.message_user(request, f'{count} user(s) deactivated successfully.')
    deactivate_users.short_description = 'Deactivate selected users'
    
    def activate_users(self, request, queryset):
        """Bulk activate users"""
        count = queryset.update(is_active=True)
        self.message_user(request, f'{count} user(s) activated successfully.')
    activate_users.short_description = 'Activate selected users'
    
    def send_welcome_email(self, request, queryset):
        """Send welcome email to selected users"""
        count = 0
        for user in queryset:
            if user.email and user.email_notifications:
                # Create notification (will be sent by background task)
                EmailNotification.objects.create(
                    user=user,
                    notification_type='welcome',
                    subject=f'Welcome to MyBlog, {user.get_short_name()}!',
                    content='Welcome email content'
                )
                count += 1
        self.message_user(request, f'Welcome email queued for {count} user(s).')
    send_welcome_email.short_description = 'Send welcome email to selected users'


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    """Standalone admin interface for Profile"""
    
    list_display = (
        'user_with_avatar',
        'bio_preview',
        'has_website',
        'social_links_count',
        'updated_at'
    )
    
    list_filter = ('updated_at',)
    
    search_fields = (
        'user__username',
        'user__email',
        'user__first_name',
        'user__last_name',
        'bio'
    )
    
    readonly_fields = ('user', 'updated_at', 'profile_picture_preview')
    
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Profile Picture', {
            'fields': ('profile_picture', 'profile_picture_preview')
        }),
        ('Biography', {
            'fields': ('bio',)
        }),
        ('Links', {
            'fields': ('website', 'twitter_url', 'linkedin_url', 'github_url')
        }),
        ('AI & Analytics', {
            'fields': ('interests', 'ai_preferences'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('updated_at',),
            'classes': ('collapse',)
        }),
    )
    
    def user_with_avatar(self, obj):
        """Display user with avatar"""
        if obj.profile_picture:
            return format_html(
                '<div style="display: flex; align-items: center; gap: 10px;">'
                '<img src="{}" style="width: 40px; height: 40px; border-radius: 50%; object-fit: cover;" />'
                '<strong>{}</strong>'
                '</div>',
                obj.profile_picture.url,
                obj.user.username
            )
        return format_html(
            '<div style="display: flex; align-items: center; gap: 10px;">'
            '<div style="width: 40px; height: 40px; border-radius: 50%; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); '
            'display: flex; align-items: center; justify-content: center; color: white; font-weight: bold;">{}</div>'
            '<strong>{}</strong>'
            '</div>',
            obj.user.username[0].upper() if obj.user.username else '?',
            obj.user.username
        )
    user_with_avatar.short_description = 'User'
    
    def profile_picture_preview(self, obj):
        """Show profile picture preview"""
        if obj.profile_picture:
            return format_html(
                '<img src="{}" style="max-width: 200px; max-height: 200px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);" />',
                obj.profile_picture.url
            )
        return format_html('<em style="color: #999;">No image uploaded</em>')
    profile_picture_preview.short_description = 'Preview'
    
    def bio_preview(self, obj):
        """Show truncated bio"""
        if obj.bio:
            bio = obj.bio[:80]
            if len(obj.bio) > 80:
                bio += '...'
            return format_html('<em>{}</em>', bio)
        return format_html('<span style="color: #999;">No bio</span>')
    bio_preview.short_description = 'Bio'
    
    def has_website(self, obj):
        """Check if website is set"""
        if obj.website:
            return format_html(
                '<a href="{}" target="_blank" style="color: #667eea;">🔗 Visit</a>',
                obj.website
            )
        return format_html('<span style="color: #999;">-</span>')
    has_website.short_description = 'Website'
    
    def social_links_count(self, obj):
        """Count social links"""
        count = sum([
            bool(obj.twitter_url),
            bool(obj.linkedin_url),
            bool(obj.github_url)
        ])
        
        if count == 0:
            return format_html('<span style="color: #999;">No links</span>')
        
        links = []
        if obj.twitter_url:
            links.append('🐦')
        if obj.linkedin_url:
            links.append('💼')
        if obj.github_url:
            links.append('💻')
        
        return format_html(
            '<span style="background: #667eea; color: white; padding: 3px 10px; '
            'border-radius: 6px; font-size: 11px;">{} {}</span>',
            ' '.join(links),
            f'{count} link{"s" if count > 1 else ""}'
        )
    social_links_count.short_description = 'Social Links'
    
    def has_add_permission(self, request):
        """Disable manual profile creation (auto-created with user)"""
        return False


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    """Admin interface for Follow relationships"""
    
    list_display = (
        'follower_display',
        'arrow',
        'following_display',
        'relationship_age',
        'created_at'
    )
    
    list_filter = ('created_at',)
    
    search_fields = (
        'follower__username',
        'follower__email',
        'following__username',
        'following__email'
    )
    
    readonly_fields = ('created_at',)
    
    ordering = ('-created_at',)
    
    date_hierarchy = 'created_at'
    
    def follower_display(self, obj):
        """Display follower with link"""
        return format_html(
            '<a href="{}" style="color: #667eea; font-weight: bold;">@{}</a>',
            reverse('admin:users_customuser_change', args=[obj.follower.pk]),
            obj.follower.username
        )
    follower_display.short_description = 'Follower'
    
    def arrow(self, obj):
        """Visual arrow"""
        return format_html('<span style="font-size: 18px; color: #764ba2;">→</span>')
    arrow.short_description = ''
    
    def following_display(self, obj):
        """Display following with link"""
        return format_html(
            '<a href="{}" style="color: #667eea; font-weight: bold;">@{}</a>',
            reverse('admin:users_customuser_change', args=[obj.following.pk]),
            obj.following.username
        )
    following_display.short_description = 'Following'
    
    def relationship_age(self, obj):
        """Show how long they've been following"""
        from django.utils.timesince import timesince
        return format_html(
            '<span style="color: #6b7280;">{} ago</span>',
            timesince(obj.created_at).split(',')[0]
        )
    relationship_age.short_description = 'Following Since'


@admin.register(EmailVerificationOTP)
class EmailVerificationOTPAdmin(admin.ModelAdmin):
    """Admin interface for Email Verification OTPs"""
    
    list_display = (
        'user_display',
        'email',
        'otp_display',
        'status_badge',
        'attempts_display',
        'created_at',
        'expires_at_display'
    )
    
    list_filter = ('is_used', 'created_at')
    
    search_fields = (
        'user__username',
        'user__email',
        'email',
        'otp'
    )
    
    readonly_fields = ('user', 'email', 'otp', 'created_at', 'expires_at', 'attempts')
    
    ordering = ('-created_at',)
    
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('User & Email', {
            'fields': ('user', 'email')
        }),
        ('OTP Details', {
            'fields': ('otp', 'is_used', 'attempts')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'expires_at')
        }),
    )
    
    def user_display(self, obj):
        """Display user with link"""
        return format_html(
            '<a href="{}" style="color: #667eea; font-weight: bold;">@{}</a>',
            reverse('admin:users_customuser_change', args=[obj.user.pk]),
            obj.user.username
        )
    user_display.short_description = 'User'
    
    def otp_display(self, obj):
        """Display OTP with styling"""
        return format_html(
            '<code style="background: #f3f4f6; padding: 5px 10px; border-radius: 6px; '
            'font-size: 14px; font-weight: bold; letter-spacing: 2px;">{}</code>',
            obj.otp
        )
    otp_display.short_description = 'OTP Code'
    
    def status_badge(self, obj):
        """Show OTP status"""
        if obj.is_used:
            return format_html(
                '<span style="background: #10b981; color: white; padding: 3px 8px; '
                'border-radius: 6px; font-size: 11px; font-weight: bold;">✓ USED</span>'
            )
        
        if timezone.now() > obj.expires_at:
            return format_html(
                '<span style="background: #ef4444; color: white; padding: 3px 8px; '
                'border-radius: 6px; font-size: 11px; font-weight: bold;">⏱ EXPIRED</span>'
            )
        
        return format_html(
            '<span style="background: #f59e0b; color: white; padding: 3px 8px; '
            'border-radius: 6px; font-size: 11px; font-weight: bold;">⏳ PENDING</span>'
        )
    status_badge.short_description = 'Status'
    
    def attempts_display(self, obj):
        """Show attempts with visual indicator"""
        if obj.attempts >= 3:
            color = '#ef4444'
            icon = '🚫'
        elif obj.attempts >= 2:
            color = '#f59e0b'
            icon = '⚠️'
        else:
            color = '#10b981'
            icon = '✓'
        
        return format_html(
            '<span style="color: {};">{} {}/3</span>',
            color,
            icon,
            obj.attempts
        )
    attempts_display.short_description = 'Attempts'
    
    def expires_at_display(self, obj):
        """Show expiry time with relative time"""
        from django.utils.timesince import timeuntil, timesince
        
        if timezone.now() > obj.expires_at:
            return format_html(
                '<span style="color: #ef4444;">Expired {} ago</span>',
                timesince(obj.expires_at).split(',')[0]
            )
        
        return format_html(
            '<span style="color: #10b981;">Expires in {}</span>',
            timeuntil(obj.expires_at).split(',')[0]
        )
    expires_at_display.short_description = 'Expires'
    
    def has_add_permission(self, request):
        """Disable manual OTP creation"""
        return False


@admin.register(EmailNotification)
class EmailNotificationAdmin(admin.ModelAdmin):
    """Admin interface for Email Notifications"""
    
    list_display = (
        'user_display',
        'notification_type_badge',
        'subject_preview',
        'status_badge',
        'created_at',
        'sent_at',
        'actions_column'
    )
    
    list_filter = (
        'notification_type',
        'status',
        'created_at',
        'sent_at'
    )
    
    search_fields = (
        'user__username',
        'user__email',
        'subject',
        'content'
    )
    
    readonly_fields = (
        'user',
        'notification_type',
        'subject',
        'content',
        'status',
        'sent_at',
        'error_message',
        'created_at',
        'context_data_display'
    )
    
    ordering = ('-created_at',)
    
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Recipient', {
            'fields': ('user',)
        }),
        ('Email Details', {
            'fields': ('notification_type', 'subject', 'content')
        }),
        ('Status', {
            'fields': ('status', 'sent_at', 'error_message')
        }),
        ('Context Data', {
            'fields': ('context_data_display',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['resend_failed_notifications', 'mark_as_sent']
    
    def user_display(self, obj):
        """Display user with link"""
        return format_html(
            '<a href="{}" style="color: #667eea; font-weight: bold;">{}</a><br>'
            '<span style="color: #6b7280; font-size: 11px;">{}</span>',
            reverse('admin:users_customuser_change', args=[obj.user.pk]),
            obj.user.username,
            obj.user.email
        )
    user_display.short_description = 'User'
    
    def notification_type_badge(self, obj):
        """Display notification type as badge"""
        type_colors = {
            'login': '#3b82f6',
            'new_post': '#10b981',
            'new_comment': '#8b5cf6',
            'comment_reply': '#ec4899',
            'new_like': '#ef4444',
            'new_follower': '#f59e0b',
            'password_reset': '#ef4444',
            'account_update': '#06b6d4',
            'welcome': '#10b981',
        }
        
        type_icons = {
            'login': '🔐',
            'new_post': '📝',
            'new_comment': '💬',
            'comment_reply': '↩️',
            'new_like': '❤️',
            'new_follower': '👥',
            'password_reset': '🔑',
            'account_update': '⚙️',
            'welcome': '👋',
        }
        
        color = type_colors.get(obj.notification_type, '#6b7280')
        icon = type_icons.get(obj.notification_type, '📧')
        
        return format_html(
            '<span style="background: {}; color: white; padding: 4px 10px; '
            'border-radius: 6px; font-size: 11px; font-weight: bold; white-space: nowrap;">'
            '{} {}</span>',
            color,
            icon,
            obj.get_notification_type_display()
        )
    notification_type_badge.short_description = 'Type'
    
    def subject_preview(self, obj):
        """Show subject with truncation"""
        if len(obj.subject) > 50:
            return format_html(
                '<span title="{}">{}</span>',
                obj.subject,
                obj.subject[:50] + '...'
            )
        return obj.subject
    subject_preview.short_description = 'Subject'
    
    def status_badge(self, obj):
        """Show status as badge"""
        status_config = {
            'pending': ('#f59e0b', '⏳'),
            'sent': ('#10b981', '✓'),
            'failed': ('#ef4444', '✗'),
        }
        
        color, icon = status_config.get(obj.status, ('#6b7280', '?'))
        
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; '
            'border-radius: 6px; font-size: 11px; font-weight: bold;">{} {}</span>',
            color,
            icon,
            obj.get_status_display().upper()
        )
    status_badge.short_description = 'Status'
    
    def actions_column(self, obj):
        """Show action buttons"""
        if obj.status == 'failed':
            return format_html(
                '<a href="#" onclick="return false;" style="color: #667eea; text-decoration: none; font-weight: bold;">'
                '🔄 Retry</a>'
            )
        return '-'
    actions_column.short_description = 'Actions'
    
    def context_data_display(self, obj):
        """Display context data as formatted JSON"""
        import json
        if obj.context_data:
            return format_html(
                '<pre style="background: #f3f4f6; padding: 10px; border-radius: 6px; overflow-x: auto;">{}</pre>',
                json.dumps(obj.context_data, indent=2)
            )
        return format_html('<em style="color: #999;">No context data</em>')
    context_data_display.short_description = 'Context Data'
    
    def resend_failed_notifications(self, request, queryset):
        """Resend failed notifications"""
        failed = queryset.filter(status='failed')
        count = 0
        for notification in failed:
            notification.status = 'pending'
            notification.error_message = ''
            notification.save(update_fields=['status', 'error_message'])
            # Trigger send (you may want to use Celery here)
            notification.send()
            count += 1
        self.message_user(request, f'{count} notification(s) queued for resending.')
    resend_failed_notifications.short_description = 'Resend failed notifications'
    
    def mark_as_sent(self, request, queryset):
        """Manually mark notifications as sent"""
        count = queryset.update(status='sent', sent_at=timezone.now())
        self.message_user(request, f'{count} notification(s) marked as sent.')
    mark_as_sent.short_description = 'Mark as sent'
    
    def has_add_permission(self, request):
        """Disable manual notification creation"""
        return False


@admin.register(LoginLog)
class LoginLogAdmin(admin.ModelAdmin):
    """Admin interface for Login Logs"""
    
    list_display = (
        'user_display',
        'login_time',
        'ip_address_display',
        'location_display',
        'suspicious_badge',
        'notification_badge',
        'device_info'
    )
    
    list_filter = (
        'is_suspicious',
        'notification_sent',
        'login_time'
    )
    
    search_fields = (
        'user__username',
        'user__email',
        'ip_address',
        'location',
        'user_agent'
    )
    
    readonly_fields = (
        'user',
        'ip_address',
        'user_agent',
        'user_agent_parsed',
        'location',
        'login_time',
        'is_suspicious',
        'notification_sent'
    )
    
    ordering = ('-login_time',)
    
    date_hierarchy = 'login_time'
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'login_time')
        }),
        ('Login Details', {
            'fields': ('ip_address', 'location')
        }),
        ('Device Information', {
            'fields': ('user_agent', 'user_agent_parsed')
        }),
        ('Security', {
            'fields': ('is_suspicious', 'notification_sent')
        }),
    )
    
    actions = ['mark_as_suspicious', 'mark_as_safe', 'send_security_notification']
    
    def user_display(self, obj):
        """Display user with link"""
        return format_html(
            '<a href="{}" style="color: #667eea; font-weight: bold;">@{}</a>',
            reverse('admin:users_customuser_change', args=[obj.user.pk]),
            obj.user.username
        )
    user_display.short_description = 'User'
    
    def ip_address_display(self, obj):
        """Display IP with lookup link"""
        return format_html(
            '<code style="background: #f3f4f6; padding: 3px 8px; border-radius: 4px; font-size: 12px;">{}</code><br>'
            '<a href="https://www.ipaddress.com/ipv4/{}" target="_blank" style="color: #667eea; font-size: 11px;">🔍 Lookup</a>',
            obj.ip_address,
            obj.ip_address
        )
    ip_address_display.short_description = 'IP Address'
    
    def location_display(self, obj):
        """Display location with icon"""
        if obj.location:
            return format_html(
                '<span style="color: #6b7280;">📍 {}</span>',
                obj.location
            )
        return format_html('<span style="color: #999;">Unknown</span>')
    location_display.short_description = 'Location'
    
    def suspicious_badge(self, obj):
        """Show suspicious status"""
        if obj.is_suspicious:
            return format_html(
                '<span style="background: #ef4444; color: white; padding: 3px 8px; '
                'border-radius: 6px; font-size: 11px; font-weight: bold;">⚠️ SUSPICIOUS</span>'
            )
        return format_html(
            '<span style="background: #10b981; color: white; padding: 3px 8px; '
            'border-radius: 6px; font-size: 11px; font-weight: bold;">✓ SAFE</span>'
        )
    suspicious_badge.short_description = 'Security Status'
    
    def notification_badge(self, obj):
        """Show if notification was sent"""
        if obj.notification_sent:
            return format_html(
                '<span style="color: #10b981;">✓ Sent</span>'
            )
        return format_html(
            '<span style="color: #6b7280;">- Not sent</span>'
        )
    notification_badge.short_description = 'Notification'
    
    def device_info(self, obj):
        """Parse and display device info from user agent"""
        import re
        
        # Simple parsing of user agent
        ua = obj.user_agent.lower()
        
        # Detect browser
        if 'chrome' in ua and 'edg' not in ua:
            browser = '🌐 Chrome'
        elif 'firefox' in ua:
            browser = '🦊 Firefox'
        elif 'safari' in ua and 'chrome' not in ua:
            browser = '🧭 Safari'
        elif 'edg' in ua:
            browser = '🌊 Edge'
        else:
            browser = '🌐 Other'
        
        # Detect OS
        if 'windows' in ua:
            os = '💻 Windows'
        elif 'mac' in ua:
            os = '🍎 macOS'
        elif 'linux' in ua:
            os = '🐧 Linux'
        elif 'android' in ua:
            os = '📱 Android'
        elif 'iphone' in ua or 'ipad' in ua:
            os = '📱 iOS'
        else:
            os = '💻 Other'
        
        return format_html(
            '<span style="color: #6b7280; font-size: 12px;">{} · {}</span>',
            browser,
            os
        )
    device_info.short_description = 'Device'
    
    def user_agent_parsed(self, obj):
        """Display formatted user agent"""
        return format_html(
            '<div style="background: #f3f4f6; padding: 10px; border-radius: 6px; font-size: 12px; '
            'font-family: monospace; word-break: break-all; max-width: 600px;">{}</div>',
            obj.user_agent
        )
    user_agent_parsed.short_description = 'Full User Agent'
    
    def mark_as_suspicious(self, request, queryset):
        """Mark selected logins as suspicious"""
        count = queryset.update(is_suspicious=True)
        self.message_user(request, f'{count} login(s) marked as suspicious.')
    mark_as_suspicious.short_description = 'Mark as suspicious'
    
    def mark_as_safe(self, request, queryset):
        """Mark selected logins as safe"""
        count = queryset.update(is_suspicious=False)
        self.message_user(request, f'{count} login(s) marked as safe.')
    mark_as_safe.short_description = 'Mark as safe'
    
    def send_security_notification(self, request, queryset):
        """Send security notification for selected logins"""
        count = 0
        for login_log in queryset.filter(notification_sent=False):
            # Create notification
            EmailNotification.objects.create(
                user=login_log.user,
                notification_type='login',
                subject=f'New login to your MyBlog account',
                content=f'New login from {login_log.ip_address}',
                context_data={
                    'ip_address': login_log.ip_address,
                    'location': login_log.location,
                    'login_time': login_log.login_time.isoformat(),
                    'is_suspicious': login_log.is_suspicious
                }
            )
            login_log.notification_sent = True
            login_log.save(update_fields=['notification_sent'])
            count += 1
        
        self.message_user(request, f'Security notification queued for {count} login(s).')
    send_security_notification.short_description = 'Send security notification'
    
    def has_add_permission(self, request):
        """Disable manual login log creation"""
        return False


# Customize admin site header and titles
admin.site.site_header = 'MyBlog Administration'
admin.site.site_title = 'MyBlog Admin'
admin.site.index_title = 'Welcome to MyBlog Admin Panel'


# Optional: Create custom admin dashboard
class CustomAdminSite(admin.AdminSite):
    """Custom admin site with additional features"""
    
    site_header = 'MyBlog Administration'
    site_title = 'MyBlog Admin Portal'
    index_title = 'Dashboard'
    
    def index(self, request, extra_context=None):
        """Custom admin index with statistics"""
        extra_context = extra_context or {}
        
        # Get statistics
        from django.db.models import Count, Q
        from datetime import timedelta
        
        now = timezone.now()
        week_ago = now - timedelta(days=7)
        
        extra_context['stats'] = {
            'total_users': CustomUser.objects.count(),
            'active_users': CustomUser.objects.filter(is_active=True).count(),
            'new_users_week': CustomUser.objects.filter(date_joined__gte=week_ago).count(),
            'verified_emails': CustomUser.objects.filter(email_verified=True).count(),
            'total_follows': Follow.objects.count(),
            'pending_otps': EmailVerificationOTP.objects.filter(is_used=False, expires_at__gt=now).count(),
            'pending_notifications': EmailNotification.objects.filter(status='pending').count(),
            'failed_notifications': EmailNotification.objects.filter(status='failed').count(),
            'suspicious_logins': LoginLog.objects.filter(is_suspicious=True).count(),
        }
        
        # Recent activity
        extra_context['recent_users'] = CustomUser.objects.order_by('-date_joined')[:5]
        extra_context['recent_logins'] = LoginLog.objects.order_by('-login_time')[:10]
        extra_context['failed_emails'] = EmailNotification.objects.filter(status='failed').order_by('-created_at')[:5]
        
        return super().index(request, extra_context)


# Uncomment to use custom admin site
# admin_site = CustomAdminSite(name='custom_admin')
# Then register models with admin_site instead of admin.site