"""
attendance_tags.py — Custom Template Filters and Tags
======================================================
Registered as 'attendance_tags' template tag library.
Usage in templates: {% load attendance_tags %}

Available filters:
  - get_item: Access dictionary value by key in templates
  - percentage_color: Return Bootstrap color class based on percentage
  - subtract: Subtract one number from another
"""

from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """
    Access a dictionary value by key in Django templates.
    Django templates don't support dict[key] syntax directly.

    Usage: {{ my_dict|get_item:key_variable }}
    Example: {{ existing_map|get_item:student.id }}
    """
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None


@register.filter
def percentage_color(value):
    """
    Returns Bootstrap color class based on attendance percentage.

    >= 75%  → 'success' (green)
    >= 60%  → 'warning' (yellow)
    < 60%   → 'danger'  (red)

    Usage: {% with color=pct|percentage_color %}
           <span class="badge bg-{{ color }}">{{ pct }}%</span>
           {% endwith %}
    """
    try:
        value = float(value)
        if value >= 75:
            return 'success'
        elif value >= 60:
            return 'warning'
        else:
            return 'danger'
    except (TypeError, ValueError):
        return 'secondary'


@register.filter
def subtract(value, arg):
    """
    Subtract arg from value.
    Usage: {{ total|subtract:present }}
    """
    try:
        return int(value) - int(arg)
    except (TypeError, ValueError):
        return 0


@register.filter
def multiply(value, arg):
    """
    Multiply value by arg.
    Usage: {{ value|multiply:100 }}
    """
    try:
        return round(float(value) * float(arg), 1)
    except (TypeError, ValueError):
        return 0
