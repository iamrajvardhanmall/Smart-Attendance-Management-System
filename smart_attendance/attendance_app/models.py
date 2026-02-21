from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import datetime


class StudentProfile(models.Model):
    YEAR_CHOICES = [
        (1, '1st Year'),
        (2, '2nd Year'),
        (3, '3rd Year'),
        (4, '4th Year'),
    ]

    user         = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    roll_no      = models.CharField(max_length=20, unique=True)
    department   = models.CharField(max_length=100)
    year         = models.IntegerField(choices=YEAR_CHOICES, default=3)
    parent_email = models.EmailField(blank=True, null=True)
    section      = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Class section assigned by admin (e.g. 'A', 'B'). Must match faculty section."
    )
    photo        = models.ImageField(upload_to='student_photos/', blank=True, null=True)
    face_label   = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Auto-assigned integer label used in OpenCV LBPH face model training."
    )

    def __str__(self):
        section_str = f" | Sec {self.section}" if self.section else ""
        return f"{self.user.get_full_name()} ({self.roll_no}{section_str})"

    class Meta:
        verbose_name = "Student Profile"
        ordering = ['roll_no']


class FacultyProfile(models.Model):
    user        = models.OneToOneField(User, on_delete=models.CASCADE, related_name='faculty_profile')
    department  = models.CharField(max_length=100)
    employee_id = models.CharField(max_length=20, unique=True)
    # Section assigned by admin (e.g. 'A', 'B', 'A & B', '3rd Year - Section A')
    section     = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Class section(s) assigned to this faculty, e.g. 'A', 'B', 'A & B'"
    )

    def __str__(self):
        section_str = f" | Section {self.section}" if self.section else ""
        return f"Prof. {self.user.get_full_name()} ({self.department}{section_str})"

    class Meta:
        verbose_name = "Faculty Profile"


class Subject(models.Model):
    name     = models.CharField(max_length=200)
    code     = models.CharField(max_length=20, unique=True)
    faculty  = models.ForeignKey(FacultyProfile, on_delete=models.CASCADE, related_name='subjects')
    semester = models.IntegerField(default=1)

    def __str__(self):
        return f"{self.name} ({self.code})"

    class Meta:
        verbose_name = "Subject"
        ordering = ['code']


class Attendance(models.Model):
    STATUS_CHOICES = [
        ('P', 'Present'),
        ('A', 'Absent'),
    ]

    student   = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='attendances')
    subject   = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='attendances')
    date      = models.DateField()
    status    = models.CharField(max_length=1, choices=STATUS_CHOICES, default='A')
    marked_by = models.ForeignKey(FacultyProfile, on_delete=models.SET_NULL, null=True, related_name='marked_attendances')
    marked_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student} | {self.subject.code} | {self.date} | {self.get_status_display()}"

    class Meta:
        verbose_name = "Attendance"
        unique_together = ['student', 'subject', 'date']
        ordering = ['-date']


class AbsenteeLog(models.Model):
    student           = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='absentee_logs')
    subject           = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='absentee_logs')
    date              = models.DateField()
    notification_sent = models.BooleanField(default=False)
    acknowledged      = models.BooleanField(default=False)

    def __str__(self):
        return f"ABSENT: {self.student} in {self.subject.code} on {self.date}"

    class Meta:
        verbose_name = "Absentee Log"
        unique_together = ['student', 'subject', 'date']
        ordering = ['-date']


class MakeUpSession(models.Model):
    subject       = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='makeup_sessions')
    date          = models.DateField()
    remedial_code = models.CharField(max_length=10, unique=True)
    expiry_time   = models.DateTimeField()
    created_by    = models.ForeignKey(FacultyProfile, on_delete=models.CASCADE, related_name='makeup_sessions')
    description   = models.TextField(blank=True, null=True, help_text="Reason or topic for make-up class")
    created_at    = models.DateTimeField(auto_now_add=True)

    def is_active(self):
        return timezone.now() < self.expiry_time

    def __str__(self):
        return f"Make-Up: {self.subject.code} | {self.date} | Code: {self.remedial_code}"

    class Meta:
        verbose_name = "Make-Up Session"
        ordering = ['-date']


class MakeUpAttendance(models.Model):
    student   = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='makeup_attendances')
    session   = models.ForeignKey(MakeUpSession, on_delete=models.CASCADE, related_name='makeup_attendances')
    marked_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Make-Up: {self.student} | Session: {self.session}"

    class Meta:
        verbose_name = "Make-Up Attendance"
        unique_together = ['student', 'session']
        ordering = ['-marked_at']


class Notification(models.Model):
    user      = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    message   = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read   = models.BooleanField(default=False)

    def __str__(self):
        status = "Read" if self.is_read else "Unread"
        return f"[{status}] {self.user.username}: {self.message[:60]}"

    class Meta:
        verbose_name = "Notification"
        ordering = ['-timestamp']
