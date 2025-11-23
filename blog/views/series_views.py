# blog/views/series_views.py

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse
from django.urls import reverse_lazy, reverse
from django.db.models import Count, Q, F
from django.db import models
from django.contrib import messages
from django.views import View
from django.utils import timezone

from ..models import Series, Post, Bookmark
from ..forms import SeriesForm, SeriesReorderForm


# =============================================================================
# PUBLIC-FACING SERIES VIEWS
# These views are accessible to any visitor.
# =============================================================================

class AllSeriesListView(ListView):
    """
    Public page displaying all available series with published posts.
    Includes search and filter functionality.
    """
    model = Series
    template_name = 'blog/all_series_list.html'
    context_object_name = 'series_list'
    paginate_by = 12

    def get_queryset(self):
        """
        Returns series that have at least one published post.
        Supports filtering by search query and author.
        """
        # Annotate each series with the count of published posts
        queryset = Series.objects.annotate(
            post_count=Count('posts', filter=Q(posts__status='public'))
        ).filter(
            post_count__gt=0  # Only show series with published posts
        ).select_related('author').order_by('-created_at')
        
        # Search functionality - search in title and description
        query = self.request.GET.get('q', '').strip()
        if query:
            queryset = queryset.filter(
                Q(title__icontains=query) | Q(description__icontains=query)
            )
        
        # Filter by author
        author_username = self.request.GET.get('author', '').strip()
        if author_username:
            queryset = queryset.filter(author__username=author_username)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get unique authors who have series with published posts
        # This is used for the author filter dropdown
        authors_with_series = Series.objects.filter(
            posts__status='public'
        ).values(
            'author__username', 
            'author__first_name', 
            'author__last_name'
        ).annotate(
            series_count=Count('id', distinct=True)
        ).order_by('author__first_name', 'author__last_name')
        
        context['authors'] = authors_with_series
        return context



class SeriesDetailView(DetailView):
    """
    Public page showing a single series and all its published posts in order.
    """
    model = Series
    template_name = 'blog/series_detail.html'
    context_object_name = 'series'

    def get_queryset(self):
        """
        Optimize query by prefetching related data.
        """
        return Series.objects.select_related('author').prefetch_related(
            'posts__author',
            'posts__categories',
            'posts__tags',
            'author__posts',
            'author__followers'
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        series = self.get_object()

        # Get only published posts, ordered by their position in the series
        posts_in_series = series.posts.filter(
            status='public'
        ).order_by('order_in_series').select_related('author')

        context['posts_in_series'] = posts_in_series

        # Calculate total reading time for the entire series
        total_reading_time = 0
        for post in posts_in_series:
            reading_time = post.get_reading_time()
            if reading_time:
                total_reading_time += int(reading_time)
        
        context['total_series_reading_time'] = total_reading_time


        # If user is authenticated, check read progress and bookmarks
        if self.request.user.is_authenticated:
            # Check if the user is following the author of the series
            context['is_following'] = series.author.followers.filter(
                follower=self.request.user
            ).exists()
            

            # Bookmarked posts
            bookmarked_ids = Bookmark.objects.filter(
                user=self.request.user,
                post__in=posts_in_series
            ).values_list('post_id', flat=True)
            context['bookmarked_post_ids'] = list(bookmarked_ids)
        else:
            context['is_following'] = False  # Anonymous user cannot follow
            context['bookmarked_post_ids'] = []

        return context
# =============================================================================
# USER DASHBOARD VIEWS (Author's Series Management)
# These views require the user to be logged in and are for managing their own series.
# =============================================================================

class UserSeriesListView(LoginRequiredMixin, ListView):
    """
    Dashboard page showing all series created by the logged-in user.
    """
    model = Series
    template_name = 'dashboard/series_list.html'
    context_object_name = 'series_list'
    paginate_by = 10

    def get_queryset(self):
        """
        Returns only series authored by the current user.
        Includes counts for both total posts and published posts.
        """
        return Series.objects.filter(
            author=self.request.user
        ).annotate(
            post_count=Count('posts'),
            published_count=Count('posts', filter=Q(posts__status='public'))
        ).order_by('-created_at')


class SeriesCreateView(LoginRequiredMixin, CreateView):
    """
    Form for creating a new series and selecting which posts to include.
    """
    model = Series
    form_class = SeriesForm
    template_name = 'dashboard/series_form.html'
    success_url = reverse_lazy('blog:my_series_list')

    def get_form_kwargs(self):
        """
        Pass the current user to the form so it can filter available posts.
        """
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        """
        Set the author to the current user before saving.
        """
        form.instance.author = self.request.user
        messages.success(
            self.request, 
            f'Series "{form.instance.title}" created successfully!'
        )
        return super().form_valid(form)
    
    def form_invalid(self, form):
        """
        Display error message if form validation fails.
        """
        messages.error(
            self.request, 
            'Please correct the errors below.'
        )
        return super().form_invalid(form)


class SeriesUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """
    Form for editing an existing series.
    Only accessible by the series author.
    """
    model = Series
    form_class = SeriesForm
    template_name = 'dashboard/series_form.html'
    success_url = reverse_lazy('blog:my_series_list')

    def test_func(self):
        """
        Security check: Only the series author can edit it.
        """
        series = self.get_object()
        return self.request.user == series.author

    def get_form_kwargs(self):
        """
        Pass the current user to the form.
        """
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_queryset(self):
        """
        Additional security: Only return series owned by the current user.
        """
        return Series.objects.filter(author=self.request.user)
    
    def form_valid(self, form):
        """
        Display success message after update.
        """
        messages.success(
            self.request, 
            f'Series "{form.instance.title}" updated successfully!'
        )
        return super().form_valid(form)


class SeriesManageView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    """
    Dedicated page for managing posts within a series.
    Provides drag-and-drop reordering and ability to add/remove posts.
    """
    model = Series
    template_name = 'dashboard/series_manage.html'
    context_object_name = 'series'

    def test_func(self):
        """
        Security check: Only the series author can manage it.
        """
        series = self.get_object()
        return self.request.user == series.author

    def get_queryset(self):
        """
        Only return series owned by the current user.
        """
        return Series.objects.filter(author=self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        series = self.get_object()
        
        # Get all posts currently in this series (including drafts)
        # This allows authors to manage unpublished posts in the series
        context['series_posts'] = series.posts.all().order_by('order_in_series')
        
        # Get user's other published posts that are NOT in any series
        # These are available to be added to this series
        context['available_posts'] = Post.objects.filter(
            author=self.request.user,
            status='public',
            series__isnull=True  # Not in any series
        ).order_by('-published_date')
        
        return context


class SeriesReorderView(LoginRequiredMixin, View):
    """
    AJAX endpoint for reordering posts within a series via drag-and-drop.
    Expects a comma-separated list of post IDs in the new order.
    """
    def post(self, request, slug):
        # Get the series and verify ownership
        series = get_object_or_404(Series, slug=slug, author=request.user)
        
        # Create form with the post data
        form = SeriesReorderForm(request.POST, series=series)
        
        if form.is_valid():
            form.save()
            return JsonResponse({
                'status': 'success',
                'message': 'Post order updated successfully'
            })
        else:
            return JsonResponse({
                'status': 'error',
                'errors': form.errors
            }, status=400)


class SeriesAddPostView(LoginRequiredMixin, View):
    """
    AJAX endpoint for adding a post to a series.
    The post will be added at the end of the series.
    """
    def post(self, request, slug):
        # Get the series and verify ownership
        series = get_object_or_404(Series, slug=slug, author=request.user)
        post_id = request.POST.get('post_id')
        
        if not post_id:
            return JsonResponse({
                'status': 'error',
                'message': 'Post ID is required'
            }, status=400)
        
        try:
            # Get the post and verify it belongs to the current user
            post = Post.objects.get(
                id=post_id,
                author=request.user,
                status='public'  # Only allow adding published posts
            )
            
            # Check if post is already in a series
            if post.series:
                return JsonResponse({
                    'status': 'error',
                    'message': f'This post is already in the series "{post.series.title}"'
                }, status=400)
            
            # Find the highest order number in the series
            max_order = series.posts.aggregate(
                max_order=models.Max('order_in_series')
            )['max_order'] or 0
            
            # Add post to series at the end
            post.series = series
            post.order_in_series = max_order + 1
            post.save()
            
            return JsonResponse({
                'status': 'success',
                'message': 'Post added to series',
                'post_id': post.id,
                'post_title': post.title,
                'order': post.order_in_series
            })
            
        except Post.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Post not found or you do not have permission to add it'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'An error occurred: {str(e)}'
            }, status=500)


class SeriesRemovePostView(LoginRequiredMixin, View):
    """
    AJAX endpoint for removing a post from a series.
    After removal, remaining posts are reordered to fill the gap.
    """
    def post(self, request, slug):
        # Get the series and verify ownership
        series = get_object_or_404(Series, slug=slug, author=request.user)
        post_id = request.POST.get('post_id')
        
        if not post_id:
            return JsonResponse({
                'status': 'error',
                'message': 'Post ID is required'
            }, status=400)
        
        try:
            # Get the post and verify it's in this series
            post = Post.objects.get(id=post_id, series=series)
            
            # Remove from series
            post.series = None
            post.order_in_series = 0
            post.save()
            
            # Reorder remaining posts to fill the gap
            remaining_posts = series.posts.all().order_by('order_in_series')
            for index, p in enumerate(remaining_posts, start=1):
                if p.order_in_series != index:
                    p.order_in_series = index
                    p.save()
            
            return JsonResponse({
                'status': 'success',
                'message': 'Post removed from series'
            })
            
        except Post.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Post not found in this series'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'An error occurred: {str(e)}'
            }, status=500)


class SeriesDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """
    Delete a series. The posts remain but are unlinked from the series.
    """
    model = Series
    template_name = 'dashboard/series_confirm_delete.html'
    success_url = reverse_lazy('blog:my_series_list')

    def test_func(self):
        """
        Security check: Only the series author can delete it.
        """
        series = self.get_object()
        return self.request.user == series.author

    def get_queryset(self):
        """
        Only return series owned by the current user.
        """
        return Series.objects.filter(author=self.request.user)
    
    def delete(self, request, *args, **kwargs):
        """
        Before deleting, unlink all posts from this series.
        """
        series = self.get_object()
        series_title = series.title
        
        # Unlink all posts from this series
        Post.objects.filter(series=series).update(
            series=None,
            order_in_series=0
        )
        
        # Display success message
        messages.success(
            request,
            f'Series "{series_title}" has been deleted. All posts have been unlinked.'
        )
        
        return super().delete(request, *args, **kwargs)


# =============================================================================
# READING LIST VIEWS
# =============================================================================

class ReadingListView(LoginRequiredMixin, ListView):
    """
    User's private reading list showing all bookmarked posts.
    """
    model = Bookmark
    template_name = 'blog/reading_list.html'
    context_object_name = 'bookmarks'
    paginate_by = 12

    def get_queryset(self):
        """
        Return only bookmarks for the current user.
        Optimize query by prefetching related data.
        """
        return Bookmark.objects.filter(
            user=self.request.user
        ).select_related(
            'post__author'
        ).prefetch_related(
            'post__categories',
            'post__tags'
        ).order_by('-created_at')


class BookmarkToggleView(LoginRequiredMixin, View):
    """
    AJAX endpoint for toggling bookmarks (add/remove from reading list).
    Returns JSON response indicating the new bookmark state.
    """
    def post(self, request, *args, **kwargs):
        post_id = request.POST.get('post_id')
        
        if not post_id:
            return JsonResponse({
                'status': 'error',
                'message': 'Post ID is required'
            }, status=400)
        
        try:
            # Get the post and verify it's published
            post = Post.objects.get(id=post_id, status='public')
        except Post.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Post not found'
            }, status=404)
        
        try:
            # Try to get existing bookmark
            bookmark, created = Bookmark.objects.get_or_create(
                user=request.user,
                post=post
            )

            if created:
                # Bookmark was just created (added to reading list)
                is_bookmarked = True
                message = 'Added to reading list'
                
                # Increment bookmark count on the post
                Post.objects.filter(id=post_id).update(
                    bookmarks_count=F('bookmarks_count') + 1
                )
            else:
                # Bookmark already existed, so delete it (remove from reading list)
                bookmark.delete()
                is_bookmarked = False
                message = 'Removed from reading list'
                
                # Decrement bookmark count on the post
                Post.objects.filter(id=post_id).update(
                    bookmarks_count=F('bookmarks_count') - 1
                )
            
            return JsonResponse({
                'status': 'success',
                'bookmarked': is_bookmarked,
                'message': message
            })
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'An error occurred: {str(e)}'
            }, status=500)


# =============================================================================
# HELPER VIEW FOR SERIES DELETION CONFIRMATION
# =============================================================================

class SeriesConfirmDeleteView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    """
    Confirmation page before deleting a series.
    Shows information about what will happen when the series is deleted.
    """
    model = Series
    template_name = 'dashboard/series_confirm_delete.html'
    context_object_name = 'series'

    def test_func(self):
        """
        Security check: Only the series author can access this page.
        """
        series = self.get_object()
        return self.request.user == series.author

    def get_queryset(self):
        """
        Only return series owned by the current user.
        """
        return Series.objects.filter(author=self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        series = self.get_object()
        
        # Get the posts that will be affected
        context['affected_posts'] = series.posts.all().order_by('order_in_series')
        context['post_count'] = series.posts.count()
        
        return context