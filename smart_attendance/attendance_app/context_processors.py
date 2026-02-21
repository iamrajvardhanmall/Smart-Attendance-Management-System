"""
context_processors.py — Global Template Context Injectors
==========================================================
These functions run on every request and inject variables
into every template automatically (no need to pass from view).

Registered in settings.py under TEMPLATES > context_processors.
"""

from .models import Notification


def notification_count(request):
    """
    Injects 'unread_count' into every template context.

    This allows the navbar to always show the notification badge
    without needing to pass it from each view separately.

    Returns 0 if user is not authenticated (avoids errors on
    public pages like login/register).
    """
    if request.user.is_authenticated:
        count = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).count()
        return {'unread_count': count}

    # For anonymous users (login page, etc.)
    return {'unread_count': 0}
