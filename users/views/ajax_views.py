import logging
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from ..models.custom_user import CustomUser
from ..models.profile import Profile
from ..models.follow import Follow
from django.views.decorators.http import require_http_methods
import json

User = CustomUser
logger = logging.getLogger(__name__)
# AJAX Views for profile picture (optional - if you want AJAX upload)
@login_required
@require_http_methods(["POST"])
def upload_profile_picture(request):
    """Handle AJAX profile picture upload"""
    if request.FILES.get('profile_picture'):
        try:
            profile, created = Profile.objects.get_or_create(user=request.user)
            profile.profile_picture = request.FILES['profile_picture']
            profile.save()
            
            logger.info(f'Profile picture uploaded for user: {request.user.username}')
            
            return JsonResponse({
                'success': True,
                'message': 'Profile picture updated successfully!',
                'image_url': profile.get_profile_picture_url()
            })
        except Exception as e:
            logger.error(f'Error uploading profile picture for {request.user.username}: {str(e)}')
            return JsonResponse({
                'success': False,
                'message': f'Error uploading image: {str(e)}'
            }, status=400)
    
    return JsonResponse({
        'success': False,
        'message': 'No file provided'
    }, status=400)


@login_required
@require_http_methods(["POST"])
def remove_profile_picture(request):
    """Handle AJAX profile picture removal"""
    try:
        profile = Profile.objects.get(user=request.user)
        if profile.profile_picture:
            profile.profile_picture.delete()
            profile.profile_picture = None
            profile.save()
            
            logger.info(f'Profile picture removed for user: {request.user.username}')
            
            return JsonResponse({
                'success': True,
                'message': 'Profile picture removed successfully!',
                'default_image_url': profile.get_profile_picture_url()
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'No profile picture to remove'
            }, status=400)
            
    except Profile.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Profile not found'
        }, status=404)
    except Exception as e:
        logger.error(f'Error removing profile picture for {request.user.username}: {str(e)}')
        return JsonResponse({
            'success': False,
            'message': f'Error removing image: {str(e)}'
        }, status=500)

def check_email_availability(request):
    """Check if email is available during registration"""
    if request.method == 'GET':
        email = request.GET.get('email', '').strip()
        current_user_id = request.GET.get('user_id')
        
        if email:
            query = User.objects.filter(email=email)
            if current_user_id and request.user.is_authenticated:
                query = query.exclude(id=request.user.id)
            
            is_available = not query.exists()
            return JsonResponse({
                'available': is_available,
                'message': 'Email is available' if is_available else 'Email is already taken'
            })
    
    return JsonResponse({'available': False, 'message': 'Invalid request'})

def check_username_availability(request):
    """Check if username is available during registration/profile edit"""
    if request.method == 'GET':
        username = request.GET.get('username', '').strip().lower()
        current_user_id = request.GET.get('user_id')
        
        if username:
            query = User.objects.filter(username=username)
            if current_user_id and request.user.is_authenticated:
                query = query.exclude(id=request.user.id)
            
            is_available = not query.exists()
            
            if is_available:
                reserved_usernames = [
                    'admin', 'administrator', 'root', 'api', 'www', 'mail', 'ftp', 
                    'blog', 'user', 'users', 'support', 'help', 'about', 'contact',
                    'login', 'register', 'signup', 'signin', 'logout', 'profile',
                    'dashboard', 'settings', 'account', 'home', 'index'
                ]
                if username in reserved_usernames:
                    is_available = False
                    message = 'This username is reserved'
                else:
                    message = 'Username is available'
            else:
                message = 'Username is already taken'
            
            return JsonResponse({
                'available': is_available,
                'message': message
            })
    
    return JsonResponse({'available': False, 'message': 'Invalid request'})

@login_required
def toggle_follow(request, user_id):
    """Toggle follow/unfollow for a user"""
    target_user = get_object_or_404(User, id=user_id)

    if request.user == target_user:
        messages.error(request, "You cannot follow yourself.")
        return redirect("blog:home")

    if request.user.is_following(target_user):
        request.user.unfollow(target_user)
        messages.success(request, f'You unfollowed {target_user.username}.')
    else:
        request.user.follow(target_user)
        messages.success(request, f'You are now following {target_user.username}.')

    return redirect(request.META.get("HTTP_REFERER", "blog:home"))



@login_required
@require_POST
def api_toggle_follow(request):
    """
    API view to toggle follow/unfollow for a user, returning a JSON response.
    """
    try:
        data = json.loads(request.body)
        user_id_to_toggle = data.get('user_id')

        if user_id_to_toggle is None:
            return JsonResponse({'success': False, 'error': 'User ID not provided.'}, status=400)

        target_user = get_object_or_404(User, id=user_id_to_toggle)
        current_user = request.user

        if current_user == target_user:
            return JsonResponse({'success': False, 'error': 'You cannot follow yourself.'}, status=400)

        is_following_now = False
        if current_user.is_following(target_user):
            current_user.unfollow(target_user)
            is_following_now = False
        else:
            current_user.follow(target_user)
            is_following_now = True

        return JsonResponse({'success': True, 'following': is_following_now})

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


def get_user_list(request, user_id, list_type):
    """
    API view to get a list of followers or following users for the modal.
    **COMPLETE FIX - handles all edge cases**
    """
    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        # Get the target user
        target_user = get_object_or_404(User, id=user_id)
        
        # Import Follow model - adjust this import based on your project structure
        from users.models import Follow  # Change 'users' to your app name if different
        
        # Get the appropriate user list
        if list_type == 'followers':
            # Get users who follow the target user
            relationships = Follow.objects.filter(following=target_user).select_related('follower')
            users_query = [rel.follower for rel in relationships]
        elif list_type == 'following':
            # Get users that the target user follows
            relationships = Follow.objects.filter(follower=target_user).select_related('following')
            users_query = [rel.following for rel in relationships]
        else:
            return JsonResponse({'error': 'Invalid list type', 'users': []}, status=400)

        # Get list of user IDs the current logged-in user is following
        logged_in_user_following_ids = set()
        if request.user.is_authenticated:
            logged_in_user_following_ids = set(
                Follow.objects.filter(follower=request.user).values_list('following_id', flat=True)
            )

        # Build the user data list
        users_data = []
        for user in users_query:
            try:
                # Generate initials for avatar fallback
                initials = ""
                if user.first_name and user.last_name:
                    initials = (user.first_name[0] + user.last_name[0]).upper()
                elif user.first_name:
                    initials = user.first_name[0].upper()
                elif user.username:
                    initials = user.username[0].upper()
                else:
                    initials = "U"

                # Get profile picture URL safely
                avatar_url = ""
                try:
                    if hasattr(user, 'profile_picture') and user.profile_picture:
                        avatar_url = user.profile_picture.url
                except (AttributeError, ValueError, TypeError):
                    avatar_url = ""
                
                # Build user data object
                user_data = {
                    'id': user.id,
                    'username': user.username,
                    'full_name': user.get_full_name() or user.username,
                    'avatar_url': avatar_url,
                    'initials': initials,
                    'show_follow_button': request.user.is_authenticated and user.id != request.user.id,
                    'is_following': user.id in logged_in_user_following_ids
                }
                users_data.append(user_data)
                
            except Exception as user_error:
                # Log the error but continue processing other users
                print(f"Error processing user {user.id if hasattr(user, 'id') else 'unknown'}: {str(user_error)}")
                continue

        return JsonResponse({'users': users_data}, status=200)

    except Exception as e:
        # Return error with empty users list
        print(f"Error in get_user_list: {str(e)}")
        return JsonResponse({
            'error': f'Failed to load users: {str(e)}',
            'users': []
        }, status=500)