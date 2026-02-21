"""
decorators.py — Role-Based Access Control Decorators
=====================================================
Custom decorators to restrict views to specific user roles.

Usage in views.py:
    @faculty_required
    def mark_attendance(request): ...

    @student_required
    def my_attendance(request): ...
"""

from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps


def faculty_required(view_func):
    """
    Decorator that allows access only to faculty members.
    Faculty = User who has a FacultyProfile linked.

    Redirects to login if not authenticated.
    Redirects to home with error message if authenticated but not faculty.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Must be logged in first
        if not request.user.is_authenticated:
            return redirect('login')

        # Check if user has a FacultyProfile
        if not hasattr(request.user, 'faculty_profile'):
            messages.error(request, "Access denied. Faculty area only.")
            return redirect('home')

        return view_func(request, *args, **kwargs)
    return wrapper


def student_required(view_func):
    """
    Decorator that allows access only to students.
    Student = User who has a StudentProfile linked.

    Redirects to login if not authenticated.
    Redirects to home with error message if authenticated but not student.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Must be logged in first
        if not request.user.is_authenticated:
            return redirect('login')

        # Check if user has a StudentProfile
        if not hasattr(request.user, 'student_profile'):
            messages.error(request, "Access denied. Student area only.")
            return redirect('home')

        return view_func(request, *args, **kwargs)
    return wrapper
