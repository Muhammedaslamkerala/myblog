from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Count, Q
from django.utils import timezone
from .models.post import Post
from .models.category import Category
from .models.tag import Tag
from .models.series import Series
from .models.comment import Comment
from .models.bookmark import Bookmark
from .models.post_view_like import PostView, PostLike


# ===== INLINE ADMINS =====

class CommentInline(admin.TabularInline):
    """Inline comments for posts"""
    model = Comment
    extra = 0
    max_num = 10
    fields = ('author', 'body_preview', 'published_date', 'is_approved', 'is_flagged')
    readonly_fields = ('author', 'body_preview', 'published_date')
    can_delete = False
    
    def body_preview(self, obj):
        """Show truncated comment body"""
        return obj.body[:100] + '...' if len(obj.body) > 100 else obj.body
    body_preview.short_description = 'Comment'
    
    def has_add_permission(self, request, obj=None):
        return False


# ===== POST ADMIN =====

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    """Enhanced admin interface for Posts"""
    
    list_display = (
        'title_with_thumbnail',
        'author_display',
        'status_badge',
        'category_tags',
        'engagement_stats',
        'published_date',
        'actions_column'
    )
    
    list_display_links = ('title_with_thumbnail',)
    
    list_filter = (
        'status',
        'is_published',
        'is_featured',
        'allow_comments',
        'ai_generated_tags',
        'ai_generated_category',
        'created_at',
        'published_date',
        'categories',
        'tags',
        'author'
    )
    
    search_fields = (
        'title',
        'slug',
        'excerpt',
        'body',
        'author__username',
        'author__email'
    )
    
    prepopulated_fields = {'slug': ('title',)}
    
    readonly_fields = (
        'id',
       
        'word_count',
        'created_at',
        'last_modified',
        'published_date',
        'summary',
        'featured_image_preview',
        'engagement_dashboard',
        'related_posts_display'
    )
    
    filter_horizontal = ('categories', 'tags')
    
    date_hierarchy = 'published_date'
    
    ordering = ('-created_at',)
    
    save_on_top = True
    
    fieldsets = (
        ('Content', {
            'fields': ('title', 'slug', 'excerpt', 'body', 'summary')
        }),
        ('Media', {
            'fields': ('featured_image', 'featured_image_preview'),
        }),
        ('Organization', {
            'fields': ('author', 'categories', 'tags', 'series', 'order_in_series')
        }),
        ('Publication', {
            'fields': ('status', 'is_published', 'is_featured', 'published_date', 'allow_comments')
        }),
        ('SEO & Metadata', {
            'fields': ('meta_description', 'word_count'),
            'classes': ('collapse',)
        }),
        ('AI Features', {
            'fields': ('ai_generated_tags', 'ai_generated_category', 'content_chunks', 'embeddings_json'),
            'classes': ('collapse',)
        }),
        ('Engagement', {
            'fields': ('engagement_dashboard',),
            'classes': ('collapse',)
        }),
        ('Related Content', {
            'fields': ('related_posts_display',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('id', 'created_at', 'last_modified'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['make_published', 'make_draft', 'feature_posts', 'unfeature_posts', 'generate_rag_data']
    
    # Custom display methods
    def title_with_thumbnail(self, obj):
        """Display title with thumbnail"""
        if obj.featured_image:
            return format_html(
                '<div style="display: flex; align-items: center; gap: 10px;">'
                '<img src="{}" style="width: 60px; height: 60px; border-radius: 8px; object-fit: cover;" />'
                '<div><strong>{}</strong><br><small style="color: #6b7280;">{} words · {} min read</small></div>'
                '</div>',
                obj.featured_image.url,
                obj.title[:60],
                obj.word_count,
                obj.get_reading_time()
            )
        return format_html(
            '<div style="display: flex; align-items: center; gap: 10px;">'
            '<div style="width: 60px; height: 60px; border-radius: 8px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); '
            'display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; font-size: 1.5rem;">📝</div>'
            '<div><strong>{}</strong><br><small style="color: #6b7280;">{} words · {} min read</small></div>'
            '</div>',
            obj.title[:60],
            obj.word_count,
            obj.get_reading_time()
        )
    title_with_thumbnail.short_description = 'Title'
    
    def author_display(self, obj):
        """Display author with link"""
        return format_html(
            '<a href="{}" style="color: #667eea; font-weight: bold;">@{}</a>',
            reverse('admin:users_customuser_change', args=[obj.author.pk]),
            obj.author.username
        )
    author_display.short_description = 'Author'
    
    def status_badge(self, obj):
        """Show status as badge"""
        status_config = {
            'public': ('#10b981', '✓', 'PUBLIC'),
            'draft': ('#f59e0b', '📝', 'DRAFT'),
            'private': ('#ef4444', '🔒', 'PRIVATE'),
        }
        
        color, icon, text = status_config.get(obj.status, ('#6b7280', '?', obj.status.upper()))
        
        featured = ''
        if obj.is_featured:
            featured = '<br><span style="background: #8b5cf6; color: white; padding: 2px 6px; border-radius: 4px; font-size: 10px; margin-top: 4px; display: inline-block;">⭐ FEATURED</span>'
        
        return format_html(
            '<span style="background: {}; color: white; padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: bold; white-space: nowrap;">'
            '{} {}</span>{}',
            color, icon, text, featured
        )
    status_badge.short_description = 'Status'
    
    def category_tags(self, obj):
        """Display categories and tags"""
        categories = obj.categories.all()[:3]
        tags = obj.tags.all()[:3]
        
        html = ''
        
        if categories:
            for cat in categories:
                html += f'<span style="background: {cat.color}; color: white; padding: 3px 8px; border-radius: 6px; font-size: 10px; margin: 2px; display: inline-block;">{cat.name}</span>'
        
        if tags:
            html += '<br>' if html else ''
            for tag in tags:
                html += f'<span style="background: #e5e7eb; color: #374151; padding: 3px 8px; border-radius: 6px; font-size: 10px; margin: 2px; display: inline-block;">#{tag.name}</span>'
        
        if not html:
            html = '<span style="color: #999;">No categories/tags</span>'
        
        return format_html(html)
    category_tags.short_description = 'Categories & Tags'
    
    def engagement_stats(self, obj):
        """Display engagement metrics"""
        return format_html(
            '<div style="font-size: 11px;">'
            '<span style="color: #3b82f6; margin-right: 8px;">👁 {}</span>'
            '<span style="color: #ef4444; margin-right: 8px;">❤️ {}</span>'
            '<span style="color: #8b5cf6; margin-right: 8px;">💬 {}</span>'
            '<span style="color: #f59e0b;">🔖 {}</span>'
            '</div>',
            obj.views_count,
            obj.likes_count,
            obj.comments.filter(is_approved=True).count(),
            obj.bookmarks_count
        )
    engagement_stats.short_description = 'Engagement'
    
    def actions_column(self, obj):
        """Show action buttons"""
        url = obj.get_absolute_url()
        return format_html(
            '<a href="{}" target="_blank" style="color: #667eea; text-decoration: none; font-weight: bold;">'
            '👁 View</a>',
            url
        )
    actions_column.short_description = 'Actions'
    
    def featured_image_preview(self, obj):
        """Show featured image preview"""
        if obj.featured_image:
            return format_html(
                '<img src="{}" style="max-width: 400px; max-height: 300px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);" />',
                obj.featured_image.url
            )
        return format_html('<em style="color: #999;">No featured image</em>')
    featured_image_preview.short_description = 'Preview'
    
    def engagement_dashboard(self, obj):
        """Display detailed engagement dashboard"""
        if not obj.pk:
            return '-'
        
        comments_count = obj.comments.filter(is_approved=True).count()
        pending_comments = obj.comments.filter(is_approved=False).count()
        
        html = '<div style="background: #f9fafb; padding: 15px; border-radius: 10px;">'
        html += '<h3 style="margin: 0 0 15px 0; color: #374151;">Engagement Metrics</h3>'
        html += '<div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px;">'
        
        metrics = [
            ('Views', obj.views_count, '👁', '#3b82f6'),
            ('Likes', obj.likes_count, '❤️', '#ef4444'),
            ('Comments', comments_count, '💬', '#8b5cf6'),
            ('Bookmarks', obj.bookmarks_count, '🔖', '#f59e0b'),
        ]
        
        for label, value, icon, color in metrics:
            html += f'''
                <div style="background: white; padding: 12px; border-radius: 8px; border-left: 4px solid {color};">
                    <div style="color: #6b7280; font-size: 12px; margin-bottom: 4px;">{icon} {label}</div>
                    <div style="font-size: 24px; font-weight: bold; color: {color};">{value}</div>
                </div>
            '''
        
        html += '</div>'
        
        if pending_comments > 0:
            html += f'<div style="margin-top: 15px; padding: 10px; background: #fef3c7; border-left: 4px solid #f59e0b; border-radius: 8px;">'
            html += f'<strong>⚠️ {pending_comments} comment(s) pending approval</strong>'
            html += '</div>'
        
        html += '</div>'
        
        return format_html(html)
    engagement_dashboard.short_description = 'Engagement Dashboard'
    
    def related_posts_display(self, obj):
        """Display related posts"""
        if not obj.pk:
            return '-'
        
        related = obj.get_related_posts()
        
        if not related:
            return format_html('<em style="color: #999;">No related posts found</em>')
        
        html = '<div style="display: grid; gap: 10px;">'
        
        for post in related:
            html += f'''
                <a href="{reverse('admin:blog_post_change', args=[post.pk])}" 
                   style="display: flex; align-items: center; gap: 10px; padding: 10px; background: #f9fafb; 
                   border-radius: 8px; text-decoration: none; color: inherit; border: 1px solid #e5e7eb;">
                    <div style="font-weight: 600; color: #374151;">{post.title[:60]}</div>
                    <div style="margin-left: auto; font-size: 11px; color: #6b7280;">
                        👁 {post.views_count} · ❤️ {post.likes_count}
                    </div>
                </a>
            '''
        
        html += '</div>'
        
        return format_html(html)
    related_posts_display.short_description = 'Related Posts'
    
    # Custom actions
    def make_published(self, request, queryset):
        """Publish selected posts"""
        count = queryset.update(status='public', is_published=True, published_date=timezone.now())
        self.message_user(request, f'{count} post(s) published successfully.')
    make_published.short_description = 'Publish selected posts'
    
    def make_draft(self, request, queryset):
        """Convert selected posts to draft"""
        count = queryset.update(status='draft', is_published=False)
        self.message_user(request, f'{count} post(s) converted to draft.')
    make_draft.short_description = 'Convert to draft'
    
    def feature_posts(self, request, queryset):
        """Feature selected posts"""
        count = queryset.update(is_featured=True)
        self.message_user(request, f'{count} post(s) featured.')
    feature_posts.short_description = 'Feature selected posts'
    
    def unfeature_posts(self, request, queryset):
        """Unfeature selected posts"""
        count = queryset.update(is_featured=False)
        self.message_user(request, f'{count} post(s) unfeatured.')
    unfeature_posts.short_description = 'Unfeature selected posts'
    
    def generate_rag_data(self, request, queryset):
        """Generate RAG data for selected posts"""
        count = 0
        for post in queryset:
            try:
                post.prepare_rag_data()
                count += 1
            except Exception as e:
                self.message_user(request, f'Error processing {post.title}: {str(e)}', level='ERROR')
        
        if count > 0:
            self.message_user(request, f'RAG data generated for {count} post(s).')
    generate_rag_data.short_description = 'Generate RAG data'


# ===== CATEGORY ADMIN =====

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Admin interface for Categories"""
    
    list_display = (
        'name_with_color',
        'slug',
        'post_count',
        'is_active',
        'created_at'
    )
    
    list_filter = ('is_active', 'created_at')
    
    search_fields = ('name', 'description')
    
    prepopulated_fields = {'slug': ('name',)}
    
    readonly_fields = ('created_at', 'post_count_detailed')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'description')
        }),
        ('Appearance', {
            'fields': ('color', 'icon')
        }),
        ('Settings', {
            'fields': ('is_active', 'created_at')
        }),
        ('Statistics', {
            'fields': ('post_count_detailed',),
            'classes': ('collapse',)
        }),
    )
    
    def name_with_color(self, obj):
        """Display name with color badge"""
        icon_html = f'<i class="bi bi-{obj.icon}"></i> ' if obj.icon else ''
        return format_html(
            '<div style="display: flex; align-items: center; gap: 10px;">'
            '<div style="width: 20px; height: 20px; border-radius: 4px; background: {};"></div>'
            '<strong>{}{}</strong>'
            '</div>',
            obj.color,
            icon_html,
            obj.name
        )
    name_with_color.short_description = 'Category'
    
    def post_count(self, obj):
        """Display post count"""
        count = obj.posts.count()
        return format_html(
            '<span style="background: #667eea; color: white; padding: 3px 10px; border-radius: 6px; font-size: 11px; font-weight: bold;">{} posts</span>',
            count
        )
    post_count.short_description = 'Posts'
    
    def post_count_detailed(self, obj):
        """Detailed post statistics"""
        total = obj.posts.count()
        public = obj.posts.filter(status='public').count()
        draft = obj.posts.filter(status='draft').count()
        
        html = f'''
            <div style="background: #f9fafb; padding: 15px; border-radius: 10px;">
                <div style="font-size: 11px; color: #6b7280; margin-bottom: 8px;">POST STATISTICS</div>
                <div style="display: flex; gap: 15px;">
                    <div>
                        <div style="font-size: 24px; font-weight: bold; color: #374151;">{total}</div>
                        <div style="font-size: 11px; color: #6b7280;">Total</div>
                    </div>
                    <div>
                        <div style="font-size: 24px; font-weight: bold; color: #10b981;">{public}</div>
                        <div style="font-size: 11px; color: #6b7280;">Public</div>
                    </div>
                    <div>
                        <div style="font-size: 24px; font-weight: bold; color: #f59e0b;">{draft}</div>
                        <div style="font-size: 11px; color: #6b7280;">Draft</div>
                    </div>
                </div>
            </div>
        '''
        
        return format_html(html)
    post_count_detailed.short_description = 'Post Statistics'


# ===== TAG ADMIN =====

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    """Admin interface for Tags"""
    
    list_display = ('name_display', 'slug', 'post_count', 'usage_trend')
    
    search_fields = ('name',)
    
    prepopulated_fields = {'slug': ('name',)}
    
    ordering = ('name',)
    
    def name_display(self, obj):
        """Display tag name with hash"""
        return format_html(
            '<span style="background: #e5e7eb; color: #374151; padding: 4px 10px; border-radius: 6px; font-weight: 600;">#{}</span>',
            obj.name
        )
    name_display.short_description = 'Tag'
    
    def post_count(self, obj):
        """Display post count"""
        count = obj.posts.count()
        return format_html(
            '<span style="color: #667eea; font-weight: 600;">{} posts</span>',
            count
        )
    post_count.short_description = 'Usage'
    
    def usage_trend(self, obj):
        """Show if tag is trending"""
        from datetime import timedelta
        recent_posts = obj.posts.filter(
            created_at__gte=timezone.now() - timedelta(days=7)
        ).count()
        
        if recent_posts >= 3:
            return format_html(
                '<span style="background: #10b981; color: white; padding: 3px 8px; border-radius: 6px; font-size: 10px;">🔥 TRENDING</span>'
            )
        return '-'
    usage_trend.short_description = 'Trend'


# ===== SERIES ADMIN =====

@admin.register(Series)
class SeriesAdmin(admin.ModelAdmin):
    """Admin interface for Series"""
    
    list_display = ('title', 'author_display', 'post_count', 'created_at')
    
    list_filter = ('created_at', 'author')
    
    search_fields = ('title', 'description', 'author__username')
    
    prepopulated_fields = {'slug': ('title',)}
    
    readonly_fields = ('created_at', 'posts_in_series')
    
    fieldsets = (
        ('Series Information', {
            'fields': ('title', 'slug', 'description', 'author')
        }),
        ('Posts in Series', {
            'fields': ('posts_in_series',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def author_display(self, obj):
        """Display author with link"""
        return format_html(
            '<a href="{}" style="color: #667eea; font-weight: bold;">@{}</a>',
            reverse('admin:users_customuser_change', args=[obj.author.pk]),
            obj.author.username
        )
    author_display.short_description = 'Author'
    
    def post_count(self, obj):
        """Display post count"""
        count = obj.posts.count()
        return format_html(
            '<span style="background: #8b5cf6; color: white; padding: 3px 10px; border-radius: 6px; font-size: 11px; font-weight: bold;">{} posts</span>',
            count
        )
    post_count.short_description = 'Posts'
    
    def posts_in_series(self, obj):
        """Display all posts in series"""
        posts = obj.posts.order_by('order_in_series', '-published_date')
        
        if not posts:
            return format_html('<em style="color: #999;">No posts in this series</em>')
        
        html = '<div style="display: grid; gap: 10px;">'
        
        for idx, post in enumerate(posts, 1):
            status_color = {'public': '#10b981', 'draft': '#f59e0b', 'private': '#ef4444'}.get(post.status, '#6b7280')
            
            html += f'''
                <div style="display: flex; align-items: center; gap: 10px; padding: 10px; background: #f9fafb; 
                     border-radius: 8px; border-left: 4px solid {status_color};">
                    <div style="font-weight: bold; color: #6b7280; min-width: 30px;">#{idx}</div>
                    <a href="{reverse('admin:blog_post_change', args=[post.pk])}" 
                       style="flex-grow: 1; color: #374151; text-decoration: none; font-weight: 600;">
                        {post.title}
                    </a>
                    <div style="font-size: 11px; color: #6b7280;">
                        {post.get_status_display()} · 👁 {post.views_count}
                    </div>
                </div>
            '''
        
        html += '</div>'
        
        return format_html(html)
    posts_in_series.short_description = 'Posts'


# ===== COMMENT ADMIN =====

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    """Admin interface for Comments"""
    
    list_display = (
        'author_display',
        'post_link',
        'body_preview',
        'status_badges',
        'published_date',
        'actions_column'
    )
    
    list_filter = (
        'is_approved',
        'is_flagged',
        'published_date',
        'post'
    )
    
    search_fields = (
        'body',
        'author__username',
        'post__title'
    )
    
    readonly_fields = ('published_date', 'updated_at', 'reply_tree')
    
    date_hierarchy = 'published_date'
    
    ordering = ('-published_date',)
    
    fieldsets = (
        ('Comment Details', {
            'fields': ('post', 'author', 'body')
        }),
        ('Moderation', {
            'fields': ('is_approved', 'is_flagged', 'flagged_reason')
        }),
        ('Reply System', {
            'fields': ('parent', 'reply_tree'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('published_date', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['approve_comments', 'flag_comments', 'unflag_comments']
    
    def author_display(self, obj):
        """Display author"""
        return format_html(
            '<a href="{}" style="color: #667eea; font-weight: bold;">@{}</a>',
            reverse('admin:users_customuser_change', args=[obj.author.pk]),
            obj.author.username
        )
    author_display.short_description = 'Author'
    
    def post_link(self, obj):
        """Link to post"""
        return format_html(
            '<a href="{}" style="color: #374151; text-decoration: none;">{}</a>',
            reverse('admin:blog_post_change', args=[obj.post.pk]),
            obj.post.title[:40]
        )
    post_link.short_description = 'Post'
    
    def body_preview(self, obj):
        """Show comment preview"""
        preview = obj.body[:100] + '...' if len(obj.body) > 100 else obj.body
        
        if obj.parent:
            return format_html(
                '<div style="padding-left: 20px; border-left: 3px solid #e5e7eb;">'
                '<small style="color: #6b7280;">↳ Reply</small><br>{}</div>',
                preview
            )
        
        return preview
    body_preview.short_description = 'Comment'
    
    def status_badges(self, obj):
        """Show status badges"""
        html = ''
        
        if obj.is_approved:
            html += '<span style="background: #10b981; color: white; padding: 3px 8px; border-radius: 6px; font-size: 10px; margin-right: 4px;">✓ APPROVED</span>'
        else:
            html += '<span style="background: #f59e0b; color: white; padding: 3px 8px; border-radius: 6px; font-size: 10px; margin-right: 4px;">⏳ PENDING</span>'
        
        if obj.is_flagged:
            html += '<span style="background: #ef4444; color: white; padding: 3px 8px; border-radius: 6px; font-size: 10px;">🚩 FLAGGED</span>'
        
        if obj.is_reply:
            html += '<br><span style="background: #8b5cf6; color: white; padding: 3px 8px; border-radius: 6px; font-size: 10px; margin-top: 4px; display: inline-block;">💬 REPLY</span>'
        
        return format_html(html)
    status_badges.short_description = 'Status'
    
    def actions_column(self, obj):
        """Action links"""
        return format_html(
            '<a href="{}" target="_blank" style="color: #667eea; text-decoration: none; font-weight: bold;">👁 View</a>',
            obj.get_absolute_url()
        )
    actions_column.short_description = 'Actions'
    
    def reply_tree(self, obj):
        """Show reply tree"""
        if not obj.pk:
            return '-'
        
        replies = obj.replies.all()
        
        if not replies:
            return format_html('<em style="color: #999;">No replies</em>')
        
        html = '<div style="padding: 10px; background: #f9fafb; border-radius: 8px;">'
        
        for reply in replies:
            html += f'''
                <div style="padding: 10px; margin: 5px 0; background: white; border-left: 3px solid #667eea; border-radius: 6px;">
                    <strong>@{reply.author.username}</strong>
                    <div style="color: #6b7280; font-size: 12px; margin-top: 4px;">{reply.body[:100]}</div>
                </div>
            '''
        
        html += '</div>'
        
        return format_html(html)
    reply_tree.short_description = 'Replies'
    
    # Actions
    def approve_comments(self, request, queryset):
        count = queryset.update(is_approved=True)
        self.message_user(request, f'{count} comment(s) approved.')
    approve_comments.short_description = 'Approve selected comments'
    
    def flag_comments(self, request, queryset):
        count = queryset.update(is_flagged=True)
        self.message_user(request, f'{count} comment(s) flagged.')
    flag_comments.short_description = 'Flag selected comments'
    
    def unflag_comments(self, request, queryset):
        count = queryset.update(is_flagged=False, flagged_reason='')
        self.message_user(request, f'{count} comment(s) unflagged.')
    unflag_comments.short_description = 'Unflag selected comments'


@admin.register(Bookmark)
class BookmarkAdmin(admin.ModelAdmin):
    """Admin interface for Bookmarks"""
    
    list_display = ('user_link', 'post_link', 'created_at')
    search_fields = ('user__username', 'post__title')
    list_filter = ('created_at',)
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at',)
    
    def user_link(self, obj):
        """Link to the user's admin page"""
        url = reverse('admin:users_customuser_change', args=[obj.user.pk])
        return format_html('<a href="{}">@{}</a>', url, obj.user.username)
    user_link.short_description = 'User'
    
    def post_link(self, obj):
        """Link to the post's admin page"""
        url = reverse('admin:blog_post_change', args=[obj.post.pk])
        return format_html('<a href="{}">{}</a>', url, obj.post.title)
    post_link.short_description = 'Post'

# ===== ENGAGEMENT MODELS ADMIN =====

@admin.register(PostView)
class PostViewAdmin(admin.ModelAdmin):
    """Admin interface for Post Views"""
    
    list_display = ('post_link', 'user_link', 'ip_address', 'timestamp')
    search_fields = ('post__title', 'user__username', 'ip_address')
    list_filter = ('timestamp',)
    date_hierarchy = 'timestamp'
    
    # Make all fields read-only as this is a log
    readonly_fields = ('post', 'user', 'ip_address', 'user_agent', 'timestamp')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
        
    def user_link(self, obj):
        """Link to the user's admin page if user exists"""
        if obj.user:
            url = reverse('admin:users_customuser_change', args=[obj.user.pk])
            return format_html('<a href="{}">@{}</a>', url, obj.user.username)
        return 'Anonymous'
    user_link.short_description = 'User'
    
    def post_link(self, obj):
        """Link to the post's admin page"""
        url = reverse('admin:blog_post_change', args=[obj.post.pk])
        return format_html('<a href="{}">{}</a>', url, obj.post.title)
    post_link.short_description = 'Post'

@admin.register(PostLike)
class PostLikeAdmin(admin.ModelAdmin):
    """Admin interface for Post Likes"""
    
    list_display = ('user_link', 'post_link', 'created_at')
    search_fields = ('user__username', 'post__title')
    list_filter = ('created_at',)
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at',)

    def user_link(self, obj):
        """Link to the user's admin page"""
        url = reverse('admin:users_customuser_change', args=[obj.user.pk])
        return format_html('<a href="{}">@{}</a>', url, obj.user.username)
    user_link.short_description = 'User'
    
    def post_link(self, obj):
        """Link to the post's admin page"""
        url = reverse('admin:blog_post_change', args=[obj.post.pk])
        return format_html('<a href="{}">{}</a>', url, obj.post.title)
    post_link.short_description = 'Post'

# ===== CUSTOMIZE ADMIN SITE =====

admin.site.site_header = "My Blog Administration"
admin.site.site_title = "Blog Admin Portal"
admin.site.index_title = "Welcome to the Blog Admin Portal"