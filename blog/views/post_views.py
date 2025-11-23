from typing import Any
from django.shortcuts import render, get_object_or_404, redirect 
from django.urls import reverse_lazy, reverse
from django.db.models import Q, Count, F
from django.contrib import messages
from django.db.models.query import QuerySet
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.generic import DetailView, ListView, TemplateView
from django.views.generic.edit import FormMixin
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import get_user_model
from django.db.models import Exists, OuterRef
import logging

from ..models import Post, Category, Tag, PostView, PostLike, Bookmark, Comment
from users.models import Follow
from ..forms import CommentForm
from ..forms import PostFilterForm

logger = logging.getLogger(__name__)

User = get_user_model()

class HomeView(TemplateView):
    """Home page - separate from post listing"""
    template_name = 'blog/home.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Featured posts for home page
        context['featured_posts'] = Post.objects.featured()[:3]
        
        # Statistics
        context['total_posts'] = Post.objects.filter(is_published=True).count()
        context['total_authors'] = User.objects.filter(posts__is_published=True).distinct().count()
        context['total_readers'] = User.objects.filter(is_active=True).count()
        
        # Categories for home page
        context['categories'] = Category.objects.filter(is_active=True).annotate(
            post_count=Count('posts', filter=Q(posts__is_published=True))
        )[:6]
        
        return context

class BookmarkAnnotateMixin:
    """
    A mixin that annotates a queryset of posts with a boolean 'is_bookmarked'
    field for the currently logged-in user.
    """
    def get_queryset(self):
        # First, get the original queryset from the actual view
        queryset = super().get_queryset()

        # If the user is authenticated, annotate it
        if self.request.user.is_authenticated:
            # Create a subquery to check if a bookmark exists for the user and post
            user_bookmarks = Bookmark.objects.filter(
                user=self.request.user,
                post=OuterRef('pk')
            )
            queryset = queryset.annotate(
                is_bookmarked=Exists(user_bookmarks)
            )
            
        return queryset

class PostListView(BookmarkAnnotateMixin, ListView):
    """All posts listing page"""
    model = Post
    template_name = 'blog/post_list.html'
    context_object_name = 'post_list'
    paginate_by = 12

    def get_queryset(self):
        queryset = Post.objects.public().select_related(
            'author', 'series'
        ).prefetch_related('categories', 'tags')
        
        # Get filter parameters
        category_slug = self.request.GET.get('category')
        tag_slug = self.request.GET.get('tag')
        search_query = self.request.GET.get('search')
        sort_by = self.request.GET.get('sort', '-published_date')

        # Apply filters
        if category_slug:
            queryset = queryset.filter(categories__slug=category_slug)
        
        if tag_slug:
            queryset = queryset.filter(tags__slug=tag_slug)
            
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) |
                Q(excerpt__icontains=search_query) |
                Q(body__icontains=search_query)
            )

        # Apply sorting
        if sort_by in ['-published_date', 'published_date', '-views_count', '-likes_count', 'title', '-title']:
            queryset = queryset.order_by(sort_by)

        return queryset.distinct()

    def get_context_data(self, **kwargs: Any):
        context = super().get_context_data(**kwargs)
        
        # Categories with post counts
        context['categories'] = Category.objects.filter(is_active=True).annotate(
            post_count=Count('posts', filter=Q(posts__is_published=True))
        )
        
        # Popular tags
        context['popular_tags'] = Tag.objects.annotate(
            post_count=Count('posts', filter=Q(posts__is_published=True))
        ).filter(post_count__gt=0).order_by('-post_count')[:15]
        
        # Statistics for stats section
        context['total_posts'] = Post.objects.filter(is_published=True).count()
        context['total_authors'] = User.objects.filter(posts__is_published=True).distinct().count()
        context['total_readers'] = User.objects.filter(is_active=True).count()
        
        context['filter_form'] = PostFilterForm(self.request.GET)
        
        # Add filter context for breadcrumbs and titles
        if self.request.GET.get('category'):
            context['current_category'] = get_object_or_404(Category, slug=self.request.GET.get('category'))
        if self.request.GET.get('tag'):
            context['current_tag'] = get_object_or_404(Tag, slug=self.request.GET.get('tag'))
        if self.request.GET.get('search'):
            context['search_query'] = self.request.GET.get('search')
        
        # Add bookmarked post IDs for authenticated users
        if self.request.user.is_authenticated:
            post_ids = [post.id for post in context['post_list']]
            bookmarked_ids = Bookmark.objects.filter(
                user=self.request.user,
                post_id__in=post_ids
            ).values_list('post_id', flat=True)
            context['bookmarked_post_ids'] = list(bookmarked_ids)
        else:
            context['bookmarked_post_ids'] = []
            
        return context

class CategoryPostListView(BookmarkAnnotateMixin,ListView):
    model = Post
    template_name = 'blog/post_list.html'
    context_object_name = 'post_list'
    paginate_by = 12

    def get_queryset(self):
        self.category = get_object_or_404(Category, slug=self.kwargs['slug'])
        queryset = Post.objects.public().filter(
            categories=self.category
        ).select_related('author', 'series').prefetch_related('categories', 'tags')
        
        sort_by = self.request.GET.get('sort', '-published_date')
        if sort_by in ['-published_date', 'published_date', '-views_count', '-likes_count']:
            queryset = queryset.order_by(sort_by)

        return queryset.distinct()

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["categories"] = Category.objects.filter(is_active=True).annotate(
            post_count=Count('posts', filter=Q(posts__is_published=True))
        )
        context["current_category"] = self.category
        context["category_posts_count"] = self.get_queryset().count()
        
        # Statistics
        context['total_posts'] = Post.objects.filter(is_published=True).count()
        context['total_authors'] = User.objects.filter(posts__is_published=True).distinct().count()
        context['total_readers'] = User.objects.filter(is_active=True).count()
        
        # Popular tags
        context['popular_tags'] = Tag.objects.annotate(
            post_count=Count('posts', filter=Q(posts__is_published=True))
        ).filter(post_count__gt=0).order_by('-post_count')[:15]
        
        # Add bookmarked post IDs for authenticated users
        if self.request.user.is_authenticated:
            post_ids = [post.id for post in context['post_list']]
            bookmarked_ids = Bookmark.objects.filter(
                user=self.request.user,
                post_id__in=post_ids
            ).values_list('post_id', flat=True)
            context['bookmarked_post_ids'] = list(bookmarked_ids)
        else:
            context['bookmarked_post_ids'] = []
        
        return context

class PostDetailView(FormMixin, DetailView):
    model = Post
    template_name = 'blog/post_details.html'
    context_object_name = 'post'
    form_class = CommentForm
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    def get_object(self):
        # Allow anyone to view published posts; allow authors to view their own drafts
        base_qs = Post.objects.select_related('author', 'series').prefetch_related(
            'categories', 'tags', 'comments__author', 'comments__replies__author'
        )
        slug = self.kwargs.get('slug')
        # Try published first
        post = base_qs.filter(slug=slug, is_published=True).first()
        # If not found and user is the author, allow viewing drafts
        if not post and self.request.user.is_authenticated:
            post = base_qs.filter(slug=slug, author=self.request.user).first()
        if not post:
            raise Http404("Post not found")
        
        # Prepare RAG data if not exists (if you have this feature)
        if hasattr(post, 'content_chunks') and not post.content_chunks:
            try:
                post.prepare_rag_data()
            except:
                pass  # Silently fail if RAG is not implemented
        
        # Track view
        self.track_view(post)
        return post

    def track_view(self, post):
        """Track unique post views"""
        ip_address = self.get_client_ip()
        user = self.request.user if self.request.user.is_authenticated else None
        
        # Check if this IP/user combo has already viewed this post today
        view, created = PostView.objects.get_or_create(
            post=post,
            ip_address=ip_address,
            defaults={
                'user': user,
                'user_agent': self.request.META.get('HTTP_USER_AGENT', '')[:255]
            }
        )
        
        # Only increment view count for new views
        if created:
            Post.objects.filter(id=post.id).update(views_count=F('views_count') + 1)
            # Refresh the post object to get updated view count
            post.refresh_from_db()

    def get_client_ip(self):
        """Get client IP address"""
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return self.request.META.get('REMOTE_ADDR', '')

    def get_success_url(self):
        # Return to post detail without anchor
        return self.object.get_absolute_url()

    def get_form_kwargs(self):
        """Pass post and user to the form"""
        kwargs = super().get_form_kwargs()
        kwargs['post'] = self.get_object()
        kwargs['user'] = self.request.user if self.request.user.is_authenticated else None
        return kwargs

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        post = self.get_object()
        user = self.request.user
        
        # Get approved top-level comments with their approved replies
        comments = post.comments.filter(
            is_approved=True,
            parent=None  # Only top-level comments
        ).select_related('author').prefetch_related(
            'replies__author'
        ).order_by('-published_date')
        
        # Filter approved replies
        for comment in comments:
            comment.approved_replies = comment.replies.filter(is_approved=True)
        
        context["comments"] = comments
        
        # Related posts (if you have this method)
        if hasattr(post, 'get_related_posts'):
            context["related_posts"] = post.get_related_posts()
        
        # Reading time (if you have this method)
        if hasattr(post, 'get_reading_time'):
            context["reading_time"] = post.get_reading_time()
        else:
            # Simple calculation: ~200 words per minute
            import re
            word_count = len(re.findall(r'\w+', post.body))
            context["reading_time"] = max(1, word_count // 200)
        
        # User interactions
        if user.is_authenticated:
            context["user_liked"] = PostLike.objects.filter(
                post=post, user=user
            ).exists()
            context["is_following"] = Follow.objects.filter(
                follower=user, following=post.author
            ).exists()
            
            # Bookmark (if you have this model)
            if 'Bookmark' in globals():
                context["is_bookmarked"] = Bookmark.objects.filter(
                    user=user, post=post
                ).exists()
        else:
            context["user_liked"] = False
            context["is_following"] = False
            context["is_bookmarked"] = False
        
        # Get actual likes count
        context["likes_count"] = post.likes_count
        
        # Series context (if you have this)
        if hasattr(post, 'series') and post.series:
            context["series_posts"] = post.series.posts.filter(
                status='public'
            ).order_by('order_in_series')
        
        return context

    def post(self, request, *args, **kwargs):
        """Handle comment form submission"""
        if not request.user.is_authenticated:
            messages.error(request, 'You must be logged in to comment.')
            return redirect('users:login')
        
        self.object = self.get_object()
        form = self.get_form()
        
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def form_valid(self, form):
        """Process valid comment form - NO ANCHOR IN URL"""
        comment = form.save()
        messages.success(self.request, 'Your comment has been posted successfully!')
        
        # Redirect to the post page WITHOUT the anchor (#comment-id)
        # This prevents the #comment-14 from appearing in the URL
        return redirect(self.object.get_absolute_url())

    def form_invalid(self, form):
        """Handle invalid form"""
        messages.error(self.request, 'Please correct the errors in your comment.')
        return self.render_to_response(self.get_context_data(form=form))


        
class TagPostListView(BookmarkAnnotateMixin, ListView):
    model = Post
    template_name = 'blog/post_list.html'
    context_object_name = 'post_list'
    paginate_by = 12

    def get_queryset(self) -> QuerySet[Any]:
        self.tag = get_object_or_404(Tag, slug=self.kwargs.get('slug'))
        return Post.objects.public().filter(
            tags=self.tag
        ).select_related('author', 'series').prefetch_related('categories', 'tags')

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["tag"] = self.tag
        context["current_tag"] = self.tag
        context["tag_posts_count"] = self.get_queryset().count()
        
        # Categories
        context["categories"] = Category.objects.filter(is_active=True).annotate(
            post_count=Count('posts', filter=Q(posts__is_published=True))
        )
        
        # Statistics
        context['total_posts'] = Post.objects.filter(is_published=True).count()
        context['total_authors'] = User.objects.filter(posts__is_published=True).distinct().count()
        context['total_readers'] = User.objects.filter(is_active=True).count()
        
        # Popular tags
        context['popular_tags'] = Tag.objects.annotate(
            post_count=Count('posts', filter=Q(posts__is_published=True))
        ).filter(post_count__gt=0).order_by('-post_count')[:15]
        
        # Add bookmarked post IDs for authenticated users
        if self.request.user.is_authenticated:
            post_ids = [post.id for post in context['post_list']]
            bookmarked_ids = Bookmark.objects.filter(
                user=self.request.user,
                post_id__in=post_ids
            ).values_list('post_id', flat=True)
            context['bookmarked_post_ids'] = list(bookmarked_ids)
        else:
            context['bookmarked_post_ids'] = []
        
        return context

class SearchListView(BookmarkAnnotateMixin, ListView):
    model = Post
    template_name = 'blog/post_list.html'
    context_object_name = 'post_list'
    paginate_by = 12

    def get_queryset(self):
        query = self.request.GET.get('q', '').strip()
        if not query:
            return Post.objects.none()

        return Post.objects.public().filter(
            Q(title__icontains=query) |
            Q(excerpt__icontains=query) |
            Q(body__icontains=query) |
            Q(tags__name__icontains=query) |
            Q(categories__name__icontains=query)
        ).distinct().select_related('author', 'series').prefetch_related('categories', 'tags')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('q', '')
        context['result_count'] = self.get_queryset().count()
        
        # Add required context for template
        context['categories'] = Category.objects.filter(is_active=True).annotate(
            post_count=Count('posts', filter=Q(posts__is_published=True))
        )
        
        # Statistics
        context['total_posts'] = Post.objects.filter(is_published=True).count()
        context['total_authors'] = User.objects.filter(posts__is_published=True).distinct().count()
        context['total_readers'] = User.objects.filter(is_active=True).count()
        
        # Add bookmarked post IDs for authenticated users
        if self.request.user.is_authenticated:
            post_ids = [post.id for post in context['post_list']]
            bookmarked_ids = Bookmark.objects.filter(
                user=self.request.user,
                post_id__in=post_ids
            ).values_list('post_id', flat=True)
            context['bookmarked_post_ids'] = list(bookmarked_ids)
        else:
            context['bookmarked_post_ids'] = []
        
        return context

class ForYouPostListView(BookmarkAnnotateMixin, LoginRequiredMixin, ListView):
    """Posts from users that the current user is following"""
    model = Post
    template_name = 'blog/post_list.html'
    context_object_name = 'post_list'
    paginate_by = 12

    def get_queryset(self):
        # Get users that current user is following
        following_users = Follow.objects.filter(
            follower=self.request.user
        ).values_list('following', flat=True)
        
        # Get posts from those users
        queryset = Post.objects.public().filter(
            author__in=following_users
        ).select_related('author', 'series').prefetch_related('categories', 'tags')
        
        # Apply sorting
        sort_by = self.request.GET.get('sort', '-published_date')
        if sort_by in ['-published_date', 'published_date', '-views_count', '-likes_count', 'title', '-title']:
            queryset = queryset.order_by(sort_by)
            
        return queryset.distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Categories with post counts (for sidebar)
        context['categories'] = Category.objects.filter(is_active=True).annotate(
            post_count=Count('posts', filter=Q(posts__is_published=True))
        )
        
        # Popular tags
        context['popular_tags'] = Tag.objects.annotate(
            post_count=Count('posts', filter=Q(posts__is_published=True))
        ).filter(post_count__gt=0).order_by('-post_count')[:15]
        
        # Statistics
        context['total_posts'] = Post.objects.filter(is_published=True).count()
        context['total_authors'] = User.objects.filter(posts__is_published=True).distinct().count()
        context['total_readers'] = User.objects.filter(is_active=True).count()
        
        # For You specific context
        context['is_for_you_page'] = True
        context['following_count'] = Follow.objects.filter(follower=self.request.user).count()
        
        # Get following users for potential display
        context['following_users'] = User.objects.filter(
            id__in=Follow.objects.filter(follower=self.request.user).values_list('following', flat=True)
        )[:6]  # Show first 6 for display
        
        # Add bookmarked post IDs for authenticated users
        post_ids = [post.id for post in context['post_list']]
        bookmarked_ids = Bookmark.objects.filter(
            user=self.request.user,
            post_id__in=post_ids
        ).values_list('post_id', flat=True)
        context['bookmarked_post_ids'] = list(bookmarked_ids)
        
        return context

    def dispatch(self, request, *args, **kwargs):
        # Redirect to signup if not authenticated
        if not request.user.is_authenticated:
            messages.info(request, 'Please log in to see posts from users you follow.')
            return redirect('users:login')
        return super().dispatch(request, *args, **kwargs)