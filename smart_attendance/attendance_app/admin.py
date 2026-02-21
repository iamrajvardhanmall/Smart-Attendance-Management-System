"""
admin.py — Django Admin Configuration
======================================
Registers all models in the Django admin panel (/admin/).
Customizes the admin display with useful list columns and filters.
"""

from django.contrib import admin
from .models import (
    StudentProfile, FacultyProfile, Subject,
    Attendance, AbsenteeLog, MakeUpSession,
    MakeUpAttendance, Notification
)

# ─────────────────────────────────────────────
# STUDENT PROFILE ADMIN
# ─────────────────────────────────────────────
@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display   = ['user', 'roll_no', 'department', 'year', 'section']
    list_editable  = ['section']          # Admin can assign section inline in the list
    list_filter    = ['department', 'year', 'section']
    search_fields  = ['roll_no', 'user__username', 'user__first_name', 'user__last_name', 'section']
    fieldsets = (
        ('Login & Identity', {
            'fields': ('user', 'roll_no')
        }),
        ('Academic Details', {
            'fields': ('department', 'year', 'section', 'parent_email', 'photo'),
            'description': 'Assign section so student appears in the correct faculty attendance list.',
        }),
    )


# ─────────────────────────────────────────────
# FACULTY PROFILE ADMIN
# ─────────────────────────────────────────────
@admin.register(FacultyProfile)
class FacultyProfileAdmin(admin.ModelAdmin):
    list_display    = ['user', 'department', 'employee_id', 'section']
    list_editable   = ['section']          # Admin can set section inline in the list view
    list_filter     = ['department', 'section']
    search_fields   = ['employee_id', 'user__username', 'user__first_name', 'section']
    fieldsets = (
        ('Login & Identity', {
            'fields': ('user', 'employee_id')
        }),
        ('Academic Assignment', {
            'fields': ('department', 'section'),
            'description': 'Assign department and section(s) to this faculty member.',
        }),
    )


# ─────────────────────────────────────────────
# SUBJECT ADMIN
# ─────────────────────────────────────────────
@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display  = ['name', 'code', 'faculty', 'semester']
    list_filter   = ['semester', 'faculty__department']
    search_fields = ['name', 'code']


# ─────────────────────────────────────────────
# ATTENDANCE ADMIN
# ─────────────────────────────────────────────
@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display  = ['student', 'subject', 'date', 'status', 'marked_by']
    list_filter   = ['status', 'date', 'subject']
    search_fields = ['student__roll_no', 'subject__code']
    date_hierarchy = 'date'


# ─────────────────────────────────────────────
# ABSENTEE LOG ADMIN
# ─────────────────────────────────────────────
@admin.register(AbsenteeLog)
class AbsenteeLogAdmin(admin.ModelAdmin):
    list_display  = ['student', 'subject', 'date', 'notification_sent', 'acknowledged']
    list_filter   = ['notification_sent', 'acknowledged', 'subject']
    date_hierarchy = 'date'


# ─────────────────────────────────────────────
# MAKE-UP SESSION ADMIN
# ─────────────────────────────────────────────
@admin.register(MakeUpSession)
class MakeUpSessionAdmin(admin.ModelAdmin):
    list_display  = ['subject', 'date', 'remedial_code', 'expiry_time', 'created_by']
    list_filter   = ['subject', 'created_by']
    search_fields = ['remedial_code']
    readonly_fields = ['remedial_code']  # Code should not be manually edited


# ─────────────────────────────────────────────
# MAKE-UP ATTENDANCE ADMIN
# ─────────────────────────────────────────────
@admin.register(MakeUpAttendance)
class MakeUpAttendanceAdmin(admin.ModelAdmin):
    list_display  = ['student', 'session', 'marked_at']
    list_filter   = ['session__subject']


# ─────────────────────────────────────────────
# NOTIFICATION ADMIN
# ─────────────────────────────────────────────
@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display  = ['user', 'message', 'timestamp', 'is_read']
    list_filter   = ['is_read']
    search_fields = ['user__username', 'message']
    date_hierarchy = 'timestamp'
