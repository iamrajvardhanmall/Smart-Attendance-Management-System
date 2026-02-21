from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps


def faculty_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')

        if not hasattr(request.user, 'faculty_profile'):
            messages.error(request, "Access denied. Faculty area only.")
            return redirect('home')

        return view_func(request, *args, **kwargs)
    return wrapper


def student_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not hasattr(request.user, 'student_profile'):
            messages.error(request, "Access denied. Student area only.")
            return redirect('home')

        return view_func(request, *args, **kwargs)
    return wrapper
