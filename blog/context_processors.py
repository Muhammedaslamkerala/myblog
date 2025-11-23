from django.db.models import Count, Q
from .models import Category

def blog_context(request):
    """
    Global context processor to provide blog-wide data to all templates
    """
    return {
        'categories': Category.objects.filter(is_active=True).annotate(
            posts_count=Count('posts', filter=Q(posts__is_published=True))
        )
    }