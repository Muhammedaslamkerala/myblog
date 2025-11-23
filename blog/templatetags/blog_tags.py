# blog/templatetags/blog_tags.py
from django import template
from django.conf import settings
import re

register = template.Library()


@register.filter(name='replace_media_urls')
def replace_media_urls(content):
    """
    CKEditor5 saves images with src="/media/..."
    In production or when SITE_URL is set, we need full absolute URL
    """
    if not content:
        return content

    media_url = settings.MEDIA_URL
    site_url = getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000').rstrip('/')

    # Ensure no double slashes
    full_media_url = f"{site_url}{media_url}".replace('//media', '/media')

    # Replace src="/media/... → full URL
    content = re.sub(r'src=["\']/media/', f'src="{full_media_url}', content)

    # Also fix src="../media/..." (sometimes happens)
    content = re.sub(r'src=["\']\.\./media/', f'src="{full_media_url}', content)

    return content