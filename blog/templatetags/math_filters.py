# blog/templatetags/math_filters.py
from django import template

register = template.Library()

@register.filter
def mul(value, arg):
    """Multiply the arg and the value"""
    try:
        return int(value) * int(arg)
    except (ValueError, TypeError):
        return ''
