from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST, require_http_methods
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count, F
import json
import logging  # Add this

from ..models import Post, PostLike, Bookmark, PostView,  Series, Comment
# from comments.models import Comment
from users.models import Follow
from django.contrib.auth import get_user_model

User = get_user_model()

logger = logging.getLogger(__name__) 
# AJAX Views for interactive features
@login_required
@require_POST
def toggle_like(request):
    """Toggle like status for a post"""
    try:
        data = json.loads(request.body)
        post_id = data.get('post_id')
        
        if not post_id:
            return JsonResponse({
                'success': False,
                'error': 'Post ID required'
            }, status=400)
        
        post = get_object_or_404(Post, id=post_id, is_published=True)
        like, created = PostLike.objects.get_or_create(
            post=post,
            user=request.user
        )
        
        if not created:
            # User already liked → unlike now
            like.delete()
            Post.objects.filter(id=post.id).update(likes_count=F('likes_count') - 1)
            liked = False
            message = 'Post unliked!'
        else:
            # User just liked → add like
            Post.objects.filter(id=post.id).update(likes_count=F('likes_count') + 1)
            liked = True
            message = 'Post liked!'

        # Refresh to get the updated number
        post.refresh_from_db()
        
        return JsonResponse({
            'success': True,
            'liked': liked,
            'likes_count': post.likes_count,
            'message': message
        })
        
    except Exception as e:
        logger.error(f"Toggle like error: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required
@require_POST
def toggle_follow(request):
    """Toggle follow status for a user"""
    try:
        data = json.loads(request.body)
        author_id = data.get('author_id')
        
        if not author_id:
            return JsonResponse({
                'success': False,
                'error': 'Author ID required'
            }, status=400)
        
        author = get_object_or_404(User, id=author_id)
        
        # Don't allow following yourself
        if request.user == author:
            return JsonResponse({
                'success': False,
                'error': 'You cannot follow yourself'
            }, status=400)
        
        follow, created = Follow.objects.get_or_create(
            follower=request.user,
            following=author
        )
        
        if not created:
            follow.delete()
            following = False
            message = f'Unfollowed {author.get_full_name() or author.username}'
        else:
            following = True
            message = f'Now following {author.get_full_name() or author.username}!'
        
        return JsonResponse({
            'success': True,
            'following': following,
            'message': message
        })
        
    except Exception as e:
        logger.error(f"Toggle follow error: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required
@require_POST
def submit_reply(request):
    """Submit a reply to a comment"""
    try:
        data = json.loads(request.body)
        comment_id = data.get('comment_id')
        reply_text = data.get('reply_text', '').strip()
        
        # Validate input
        if not comment_id:
            return JsonResponse({
                'success': False,
                'error': 'Comment ID required'
            }, status=400)
        
        if not reply_text:
            return JsonResponse({
                'success': False,
                'error': 'Reply cannot be empty'
            }, status=400)
        
        if len(reply_text) < 5:
            return JsonResponse({
                'success': False,
                'error': 'Reply must be at least 5 characters long'
            }, status=400)
        
        if len(reply_text) > 500:
            return JsonResponse({
                'success': False,
                'error': 'Reply cannot exceed 500 characters'
            }, status=400)
        
        # Get parent comment
        parent_comment = get_object_or_404(Comment, id=comment_id, is_approved=True)
        
        # Create reply
        reply = Comment.objects.create(
            post=parent_comment.post,
            author=request.user,
            body=reply_text,
            parent=parent_comment,
            is_approved=True  # Auto-approve, adjust based on your needs
        )
        
        # Get author initials
        if request.user.first_name and request.user.last_name:
            author_initials = f"{request.user.first_name[0].upper()}{request.user.last_name[0].upper()}"
        else:
            author_initials = request.user.username[0].upper()
        
        return JsonResponse({
            'success': True,
            'reply': {
                'id': reply.id,
                'body': reply.body,
                'author_name': request.user.get_full_name() or request.user.username,
                'author_initials': author_initials,
                'is_author': True
            }
        })
        
    except Exception as e:
        logger.error(f"Submit reply error: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_POST
def edit_comment(request):
    """Edit an existing comment"""
    try:
        data = json.loads(request.body)
        comment_id = data.get('comment_id')
        new_text = data.get('new_text', '').strip()
        
        # Validate input
        if not comment_id:
            return JsonResponse({
                'success': False,
                'error': 'Comment ID required'
            }, status=400)
        
        if not new_text:
            return JsonResponse({
                'success': False,
                'error': 'Comment cannot be empty'
            }, status=400)
        
        if len(new_text) < 10:
            return JsonResponse({
                'success': False,
                'error': 'Comment must be at least 10 characters long'
            }, status=400)
        
        # Get comment and verify ownership
        try:
            comment = Comment.objects.get(id=comment_id, author=request.user)
        except Comment.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Comment not found or you do not have permission to edit it'
            }, status=404)
        
        # Update comment
        comment.body = new_text
        comment.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Comment updated successfully'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        logger.error(f"Edit comment error: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'An unexpected error occurred. Please try again.'
        }, status=500)


@login_required
@require_POST
def delete_comment(request):
    """Delete an existing comment"""
    try:
        data = json.loads(request.body)
        comment_id = data.get('comment_id')
        
        if not comment_id:
            return JsonResponse({
                'success': False,
                'error': 'Comment ID required'
            }, status=400)
        
        # Get comment and verify ownership
        try:
            comment = Comment.objects.get(id=comment_id, author=request.user)
        except Comment.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Comment not found or you do not have permission to delete it'
            }, status=404)
        
        # Delete comment
        comment.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Comment deleted successfully'
        })
        
    except Exception as e:
        logger.error(f"Delete comment error: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

def increment_view_count(request, slug):
    """AJAX endpoint to increment view count"""
    if request.method == 'POST':
        post = get_object_or_404(Post, slug=slug, is_published=True)
        ip_address = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0] or request.META.get('REMOTE_ADDR', '')
        
        # Check if this IP has viewed this post recently (within last hour)
        from django.utils import timezone
        from datetime import timedelta
        
        recent_view = PostView.objects.filter(
            post=post,
            ip_address=ip_address,
            viewed_at__gte=timezone.now() - timedelta(hours=1)
        ).exists()
        
        if not recent_view:
            PostView.objects.create(
                post=post,
                ip_address=ip_address,
                user=request.user if request.user.is_authenticated else None,
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:255]
            )
            post.views_count = F('views_count') + 1
            post.save(update_fields=['views_count'])
            
        return JsonResponse({'success': True})
    
    return JsonResponse({'success': False}, status=405)

@login_required
@require_http_methods(["POST"])
def bookmark_toggle_view(request):
    """
    Handles the logic for adding or removing a bookmark.
    This view is designed to be called by JavaScript (AJAX).
    """
    post_id = request.POST.get('post_id')
    post = get_object_or_404(Post, id=post_id)
    
    # The most elegant way to handle toggling:
    bookmark, created = Bookmark.objects.get_or_create(user=request.user, post=post)

    if created:
        # If a new bookmark was created, the user just bookmarked it.
        is_bookmarked = True
        post.bookmarks_count += 1
    else:
        # If it already existed, we delete it to "un-bookmark".
        bookmark.delete()
        is_bookmarked = False
        post.bookmarks_count -= 1
    
    post.save(update_fields=['bookmarks_count'])

    # Return the new status to the JavaScript.
    return JsonResponse({
        'status': 'ok',
        'bookmarked': is_bookmarked,
    })


