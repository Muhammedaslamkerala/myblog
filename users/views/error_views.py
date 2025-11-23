import logging
from django.shortcuts import render



logger = logging.getLogger(__name__)


def handler404(request, exception=None):
    """Custom 404 error handler"""
    logger.warning(f'404 Error - Page not found: {request.path} | User: {request.user} | IP: {request.META.get("REMOTE_ADDR")}')
    
    response = render(request, 'errors/404.html', {
        'request_path': request.path,
        'user': request.user,
    })
    response.status_code = 404
    return response

def handler500(request):
    """Custom 500 error handler"""
    logger.error(f'500 Error - Internal server error: {request.path} | User: {request.user} | IP: {request.META.get("REMOTE_ADDR")}')
    
    response = render(request, 'errors/500.html', {
        'request_path': request.path,
        'user': request.user,
    })
    response.status_code = 500
    return response

def handler403(request, exception=None):
    """Custom 403 error handler"""
    logger.warning(f'403 Error - Access denied: {request.path} | User: {request.user} | IP: {request.META.get("REMOTE_ADDR")}')
    
    response = render(request, 'errors/403.html', {
        'request_path': request.path,
        'user': request.user,
        'exception': str(exception) if exception else None,
    })
    response.status_code = 403
    return response

def handler400(request, exception=None):
    """Custom 400 error handler"""
    logger.warning(f'400 Error - Bad request: {request.path} | User: {request.user} | IP: {request.META.get("REMOTE_ADDR")}')
    
    response = render(request, 'errors/400.html', {
        'request_path': request.path,
        'user': request.user,
        'exception': str(exception) if exception else None,
    })
    response.status_code = 400
    return response

# CSRF Error Handler
def csrf_failure(request, reason=""):
    """Custom CSRF failure handler"""
    logger.warning(f'CSRF Error: {request.path} | User: {request.user} | Reason: {reason} | IP: {request.META.get("REMOTE_ADDR")}')
    
    return render(request, 'errors/csrf_error.html', {
        'request_path': request.path,
        'user': request.user,
        'reason': reason,
    }, status=403)