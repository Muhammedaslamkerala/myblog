from datetime import timedelta
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import CreateView, UpdateView, DeleteView, TemplateView, ListView
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q, Count, F, Sum
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models.functions import TruncDate
from django.shortcuts import render, get_object_or_404, redirect 
from django.contrib import messages
from django.utils import timezone
from django.utils.text import slugify
from django.http import JsonResponse
from django.utils.html import strip_tags
from datetime import timedelta
from django.utils.http import url_has_allowed_host_and_scheme
from django.urls import reverse
import json

from ..models import Post, Category, Tag, PostLike, PostView, Comment
from ..forms import PostForm
from users.models import Follow



def handle_post_form_logic(form, request_user, is_new_post=True, existing_post=None):
    """
    A helper function to process post submission logic for both create and edit.
    """
    post = form.save(commit=False)
    if is_new_post:
        post.author = request_user
    
    # Auto-generate excerpt if empty
    if not form.cleaned_data.get('excerpt'):
        body_text = strip_tags(post.body)
        post.excerpt = body_text[:250].strip() + ('...' if len(body_text) > 250 else '')
    
    # Handle publishing logic based on the status field
    desired_status = form.cleaned_data.get('status')
    
    was_published = False if is_new_post else existing_post.is_published

    if desired_status == 'public':
        post.is_published = True
        post.status = 'public'
        # Only set published_date if it's being published for the first time
        if not was_published:
            post.published_date = timezone.now()
        message = f'Post "{post.title}" has been published successfully!'
    elif desired_status == 'private':
        post.is_published = False
        post.status = 'private'
        message = f'Post "{post.title}" has been set to private.'
    else:  # 'draft'
        post.is_published = False
        post.status = 'draft'
        message = f'Post "{post.title}" has been saved as a draft.'

    # Auto-generate a unique slug for new posts
    if is_new_post and not post.slug:
        base_slug = slugify(post.title)
        slug = base_slug
        counter = 1
        while Post.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        post.slug = slug
    
    post.save()
    
    # Handle tags from tags_input field
    post.tags.clear()
    tags_input = form.cleaned_data.get('tags_input', '')
    if tags_input:
        tag_names = [name.strip() for name in tags_input.split(',') if name.strip()]
        for tag_name in tag_names:
            tag, _ = Tag.objects.get_or_create(name=tag_name, defaults={'slug': slugify(tag_name)})
            post.tags.add(tag)
    
    form.save_m2m() # Save many-to-many relationships
    
    return post, message


class PostCreateView(LoginRequiredMixin, CreateView):
    model = Post
    form_class = PostForm
    template_name = 'blog/post_create.html'
    success_url = reverse_lazy('blog:dashboard')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.filter(is_active=True)
        context['popular_tags'] = Tag.objects.annotate(post_count=Count('posts')).order_by('-post_count')[:15]
        return context
    
    def form_valid(self, form):
        post, message = handle_post_form_logic(form, self.request.user, is_new_post=True)
        messages.success(self.request, message)
        self.object = post
        return redirect(self.get_success_url())
    
    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors highlighted below.')
        return super().form_invalid(form)


class PostEditView(LoginRequiredMixin, UpdateView):
    model = Post
    form_class = PostForm
    template_name = 'blog/post_edit.html'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'
    
    def get_queryset(self):
        return Post.objects.filter(author=self.request.user)
    
    def dispatch(self, request, *args, **kwargs):
        # Only capture the referer on the initial GET request
        if request.method == 'GET':
            referer_url = request.META.get('HTTP_REFERER')
            
            # Security check the URL and make sure it's not the edit page itself
            if referer_url and url_has_allowed_host_and_scheme(
                url=referer_url, allowed_hosts={request.get_host()}
            ) and self.request.path not in referer_url:
                # Store the safe URL in the session
                request.session['edit_success_url'] = referer_url

        return super().dispatch(request, *args, **kwargs)

    # STEP 2: USE THE STORED URL WHEN THE FORM IS SUCCESSFULLY SUBMITTED
    def get_success_url(self):
        """
        Retrieves the success URL from the session.
        If not found, falls back to the dashboard.
        .pop() gets the value AND removes it, cleaning up the session.
        """
        fallback_url = reverse('blog:dashboard')
        # Use the URL stored in the session, or the fallback if it doesn't exist
        return self.request.session.pop('edit_success_url', fallback_url)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.filter(is_active=True)
        context['popular_tags'] = Tag.objects.annotate(post_count=Count('posts')).order_by('-post_count')[:15]
        return context
    
    def get_initial(self):
        initial = super().get_initial()
        if self.object.tags.exists():
            initial['tags_input'] = ', '.join([tag.name for tag in self.object.tags.all()])
        return initial
    
    def form_valid(self, form):
        # Handle featured image removal
        if self.request.POST.get('clear_featured_image') == 'true':
            post = self.get_object()
            post.featured_image.delete(save=False)

        post, message = handle_post_form_logic(form, self.request.user, is_new_post=False, existing_post=self.get_object())
        messages.success(self.request, message)
        self.object = post
        return redirect(self.get_success_url())

    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)

class PostDeleteView(LoginRequiredMixin, DeleteView):
    model = Post
    slug_field = 'slug'
    template_name = 'blog/post_confirm_delete.html' 
    slug_url_kwarg = 'slug'
    

    def get_queryset(self):
        """Ensures users can only delete their own posts."""
        return Post.objects.filter(author=self.request.user)

    def dispatch(self, request, *args, **kwargs):
        """
        Backend-only logic to remember where the user came from.
        This is identical to the logic in PostEditView.
        """
        # We only save the URL when the user first loads the confirmation page.
        if request.method == 'GET':
            referer_url = request.META.get('HTTP_REFERER')
            
            # Security check and save the safe URL to the session.
            if referer_url and url_has_allowed_host_and_scheme(
                url=referer_url, allowed_hosts={request.get_host()}
            ):
                request.session['post_delete_return_url'] = referer_url

        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        """
        After deletion, redirect back to the page we saved in the session.
        This is identical to the logic in PostEditView.
        """
        fallback_url = reverse('blog:dashboard')
        # .pop() gets the URL and cleans up the session.
        return self.request.session.pop('post_delete_return_url', fallback_url)

    def form_valid(self, form):
        """
        Adds a success message before deleting the post.
        """
        post_title = self.object.title
        messages.success(self.request, f'Post "{post_title}" has been deleted successfully!')
        # The parent class's form_valid handles the actual deletion
        # and then calls get_success_url() for the redirect.
        return super().form_valid(form)

# This helper function is required by the view
def calculate_percentage_change(old_value, new_value):
    """Calculate percentage change between two values."""
    if old_value == 0:
        if new_value == 0:
            return 0
        # If old was 0 and new is not, it's an infinite increase.
        # Representing as 100% is a common, practical choice.
        return 100
    change = ((new_value - old_value) / old_value) * 100
    return round(change, 1)


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'blog/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Base queryset for all posts by the logged-in user
        user_posts = Post.objects.filter(author=user)

        # --- User's posts statistics (Optimized Section) ---

        # OPTIMIZATION 1: Get all status counts in a single database query.
        status_counts = user_posts.values('status').annotate(count=Count('status')).order_by()
        counts_dict = {item['status']: item['count'] for item in status_counts}

        context['total_posts'] = user_posts.count()
        context['published_posts'] = counts_dict.get('public', 0)
        context['draft_posts'] = counts_dict.get('draft', 0)
        context['private_posts'] = counts_dict.get('private', 0)

        # OPTIMIZATION 2: Use the database to sum totals instead of Python.
        totals = user_posts.aggregate(
            total_views=Sum('views_count'),
            total_likes=Sum('likes_count')
        )
        context['total_views'] = totals.get('total_views') or 0
        context['total_likes'] = totals.get('total_likes') or 0

        # --- Recent Activity ---
        context['recent_posts'] = user_posts.order_by('-created_at')[:5]

        context['recent_comments'] = Comment.objects.filter(
            post__author=user
        ).select_related('author', 'post').order_by('-published_date')[:10]

        # --- Following/Followers and Activity Feed ---
        following_relationships = Follow.objects.filter(follower=user).select_related('following')
        following_user_ids = following_relationships.values_list('following_id', flat=True)

        context['following_count'] = len(following_user_ids)
        context['following_users'] = [rel.following for rel in following_relationships[:6]]
        context['all_following_users'] = [rel.following for rel in following_relationships]

        followers_relationships = Follow.objects.filter(following=user).select_related('follower')
        context['followers_count'] = followers_relationships.count()
        context['followers_users'] = [rel.follower for rel in followers_relationships[:6]]

        if following_user_ids:
            context['following_recent_posts'] = Post.objects.public().filter(
                author_id__in=following_user_ids
            ).select_related('author').order_by('-published_date')[:5]
        else:
            context['following_recent_posts'] = []

        # --- Chart Data and Trends ---
        period_days = int(self.request.GET.get('period', 30))
        context['chart_period'] = period_days
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=period_days - 1) # -1 to make it inclusive

        # Query data for charts
        views_data = PostView.objects.filter(
            post__author=user, timestamp__date__gte=start_date, timestamp__date__lte=end_date
        ).annotate(date=TruncDate('timestamp')).values('date').annotate(count=Count('id')).order_by('date')

        likes_data = PostLike.objects.filter(
            post__author=user, created_at__date__gte=start_date, created_at__date__lte=end_date
        ).annotate(date=TruncDate('created_at')).values('date').annotate(count=Count('id')).order_by('date')
        
        comments_data = Comment.objects.filter(
            post__author=user, published_date__date__gte=start_date, published_date__date__lte=end_date
        ).annotate(date=TruncDate('published_date')).values('date').annotate(count=Count('id')).order_by('date')

        # Prepare data for Chart.js
        date_range = [start_date + timedelta(days=x) for x in range(period_days)]
        
        views_dict = {item['date']: item['count'] for item in views_data}
        likes_dict = {item['date']: item['count'] for item in likes_data}
        comments_dict = {item['date']: item['count'] for item in comments_data}

        chart_labels = [date.strftime('%b %d') for date in date_range]
        chart_views = [views_dict.get(date, 0) for date in date_range]
        chart_likes = [likes_dict.get(date, 0) for date in date_range]
        chart_comments = [comments_dict.get(date, 0) for date in date_range]

        context['chart_data'] = json.dumps({
            'labels': chart_labels,
            'datasets': [
                {'label': 'Views', 'data': chart_views, 'borderColor': '#3b82f6', 'tension': 0.1},
                {'label': 'Likes', 'data': chart_likes, 'borderColor': '#ef4444', 'tension': 0.1},
                {'label': 'Comments', 'data': chart_comments, 'borderColor': '#22c55e', 'tension': 0.1}
            ]
        })
        
        # --- Trend Calculations ---
        half_period = period_days // 2
        mid_date = end_date - timedelta(days=half_period)

        # Trend values
        recent_views = sum(v for d, v in views_dict.items() if d >= mid_date)
        older_views = sum(v for d, v in views_dict.items() if d < mid_date)
        context['views_trend'] = calculate_percentage_change(older_views, recent_views)

        recent_likes = sum(v for d, v in likes_dict.items() if d >= mid_date)
        older_likes = sum(v for d, v in likes_dict.items() if d < mid_date)
        context['likes_trend'] = calculate_percentage_change(older_likes, recent_likes)

        recent_comments = sum(v for d, v in comments_dict.items() if d >= mid_date)
        older_comments = sum(v for d, v in comments_dict.items() if d < mid_date)
        context['comments_trend'] = calculate_percentage_change(older_comments, recent_comments)

        recent_posts = user_posts.filter(created_at__date__gte=mid_date).count()
        older_posts = user_posts.filter(created_at__date__lt=mid_date).count()
        context['posts_trend'] = calculate_percentage_change(older_posts, recent_posts)

        recent_followers = Follow.objects.filter(following=user, created_at__date__gte=mid_date).count()
        older_followers = Follow.objects.filter(following=user, created_at__date__lt=mid_date).count()
        context['followers_trend'] = calculate_percentage_change(older_followers, recent_followers)

        return context



class MyPostsView(LoginRequiredMixin, TemplateView):
    """
    Handles the "My Posts" dashboard page with separate tabs for
    published, draft, and private posts.
    """
    template_name = 'blog/my_posts.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        base_qs = Post.objects.filter(author=user).select_related(
            'author'
        ).prefetch_related('categories', 'tags', 'comments')

        # --- Paginate Published Posts ---
        published_list = base_qs.filter(status='public').order_by('-published_date')
        paginator_published = Paginator(published_list, 9)
        page_published_num = self.request.GET.get('page_published')
        
        # ✅ FIXED: Robust pagination logic that handles all edge cases
        try:
            published_posts = paginator_published.page(page_published_num)
        except (PageNotAnInteger, EmptyPage):
            # If page is not an integer or is out of range, deliver first page.
            # This works even if the list is empty.
            published_posts = paginator_published.page(1)
        
        for post in published_posts:
            post.absolute_url = self.request.build_absolute_uri(post.get_absolute_url())
        context['published_posts'] = published_posts

        # --- Paginate Draft Posts ---
        draft_list = base_qs.filter(status='draft').order_by('-last_modified')
        paginator_drafts = Paginator(draft_list, 9)
        page_drafts_num = self.request.GET.get('page_drafts')
        
        # ✅ FIXED: Robust pagination logic
        try:
            context['draft_posts'] = paginator_drafts.page(page_drafts_num)
        except (PageNotAnInteger, EmptyPage):
            context['draft_posts'] = paginator_drafts.page(1)
            
        # --- Paginate Private Posts ---
        private_list = base_qs.filter(status='private').order_by('-last_modified')
        paginator_private = Paginator(private_list, 9)
        page_private_num = self.request.GET.get('page_private')
        
        # ✅ FIXED: Robust pagination logic
        try:
            private_posts = paginator_private.page(page_private_num)
        except (PageNotAnInteger, EmptyPage):
            private_posts = paginator_private.page(1)

        for post in private_posts:
            post.absolute_url = self.request.build_absolute_uri(post.get_absolute_url())
        context['private_posts'] = private_posts

        return context

@method_decorator(csrf_exempt, name='dispatch')
class AutoSaveView(LoginRequiredMixin, View):
    def post(self, request):
        try:
            data = json.loads(request.body)
            post_id = data.get('post_id')
            
            if post_id:
                post = get_object_or_404(Post, id=post_id, author=request.user)
            else:
                post = Post(author=request.user)
            
            # Update post fields
            post.title = data.get('title', post.title)
            post.body = data.get('content', post.body)
            post.excerpt = data.get('excerpt', post.excerpt)
            post.save()
            
            return JsonResponse({
                'success': True,
                'post_id': str(post.id),
                'message': 'Auto-saved successfully'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })