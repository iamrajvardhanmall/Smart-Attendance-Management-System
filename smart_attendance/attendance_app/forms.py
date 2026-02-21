"""
forms.py — Form Validation for Smart Attendance Management System
=================================================================
All Django forms used for user input validation.
Forms handle login, attendance, make-up sessions,
and admin-only account creation (no self-registration allowed).
"""

from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from django.utils import timezone
from .models import StudentProfile, FacultyProfile, Subject, MakeUpSession


# ─────────────────────────────────────────────
# LOGIN FORM
# ─────────────────────────────────────────────
class LoginForm(AuthenticationForm):
    """
    Extends Django's built-in login form.
    Adds Bootstrap CSS classes to username/password fields.
    """
    username = forms.CharField(
        label="Registration No. / Faculty ID",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your ID (given by Admin)',
            'autofocus': True
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter password'
        })
    )


# ─────────────────────────────────────────────────────
# ADMIN-ONLY: CREATE STUDENT ACCOUNT
# Only site admin can create student accounts.
# Login ID = 8-digit Registration Number (e.g. 12345678)
# ─────────────────────────────────────────────────────
class AdminStudentCreationForm(forms.Form):
    """
    Admin fills this form to create a new student account.
    The 8-digit Registration Number becomes the student's login username.
    No self-registration is allowed.
    """
    # ── Login credentials ──────────────────────
    registration_number = forms.CharField(
        label="Registration Number (8 digits)",
        min_length=8,
        max_length=8,
        widget=forms.TextInput(attrs={
            'class':       'form-control',
            'placeholder': 'e.g. 12345678',
            'pattern':     r'\d{8}',
            'title':       'Must be exactly 8 digits',
        })
    )
    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Set a password'})
    )
    password2 = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Repeat password'})
    )

    # ── Student personal info ──────────────────
    first_name = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First name'})
    )
    last_name = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last name'})
    )
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'student@college.edu'})
    )

    # ── Academic info ──────────────────────────
    department = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. CSE'})
    )
    year = forms.ChoiceField(
        choices=StudentProfile.YEAR_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    parent_email = forms.EmailField(
        required=False,
        label="Parent Email (optional)",
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'parent@gmail.com'})
    )
    section = forms.CharField(
        label="Section (optional)",
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class':       'form-control',
            'placeholder': "e.g. A, B, A & B",
        }),
        help_text="Must match the faculty's section so the student appears in their attendance list."
    )

    photo = forms.ImageField(
        required=False,
        label="Student Photo (for Face Recognition)",
        widget=forms.FileInput(attrs={
            'class':  'form-control',
            'accept': 'image/jpeg,image/png,image/jpg',
        }),
        help_text="Upload a clear frontal face photo. Used to auto-mark attendance via webcam."
    )

    def clean_registration_number(self):
        """Must be exactly 8 numeric digits and not already taken."""
        reg = self.cleaned_data.get('registration_number', '')
        if not reg.isdigit():
            raise forms.ValidationError("Registration number must contain digits only.")
        if len(reg) != 8:
            raise forms.ValidationError("Registration number must be exactly 8 digits.")
        if User.objects.filter(username=reg).exists():
            raise forms.ValidationError(f"Registration number {reg} is already registered.")
        if StudentProfile.objects.filter(roll_no=reg).exists():
            raise forms.ValidationError(f"A student with roll number {reg} already exists.")
        return reg

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password1')
        p2 = cleaned_data.get('password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Passwords do not match.")
        return cleaned_data


# ─────────────────────────────────────────────────────
# ADMIN-ONLY: CREATE FACULTY ACCOUNT
# Only site admin can create faculty accounts.
# Login ID = 5-digit Faculty ID (e.g. FAC01)
# ─────────────────────────────────────────────────────
class AdminFacultyCreationForm(forms.Form):
    """
    Admin fills this form to create a new faculty account.
    The 5-character Faculty ID becomes the faculty's login username.
    No self-registration is allowed.
    """
    # ── Login credentials ──────────────────────
    faculty_id = forms.CharField(
        label="Faculty ID (5 characters, e.g. FAC01)",
        min_length=5,
        max_length=5,
        widget=forms.TextInput(attrs={
            'class':       'form-control text-uppercase',
            'placeholder': 'e.g. FAC01',
            'title':       'Must be exactly 5 characters',
        })
    )
    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Set a password'})
    )
    password2 = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Repeat password'})
    )

    # ── Faculty personal info ──────────────────
    first_name = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First name'})
    )
    last_name = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last name'})
    )
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'faculty@college.edu'})
    )

    # ── Department & Section ──────────────────
    department = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. CSE'})
    )
    section = forms.CharField(
        label="Section (optional)",
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class':       'form-control',
            'placeholder': "e.g. A, B, A & B, 3rd Year - Section A",
        }),
        help_text="Class section(s) assigned to this faculty."
    )

    def clean_faculty_id(self):
        """Must be exactly 5 characters and not already taken."""
        fid = self.cleaned_data.get('faculty_id', '').strip().upper()
        if len(fid) != 5:
            raise forms.ValidationError("Faculty ID must be exactly 5 characters.")
        if User.objects.filter(username=fid).exists():
            raise forms.ValidationError(f"Faculty ID '{fid}' is already registered.")
        if FacultyProfile.objects.filter(employee_id=fid).exists():
            raise forms.ValidationError(f"A faculty with ID '{fid}' already exists.")
        return fid

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password1')
        p2 = cleaned_data.get('password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Passwords do not match.")
        return cleaned_data


# ─────────────────────────────────────────────
# ATTENDANCE FILTER FORM
# ─────────────────────────────────────────────
class AttendanceFilterForm(forms.Form):
    """
    Used by faculty to select subject + date before
    the student list is displayed for attendance marking.
    """
    subject = forms.ModelChoiceField(
        queryset=Subject.objects.none(),  # Populated in view based on logged-in faculty
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label="-- Select Subject --"
    )
    date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'   # HTML5 date picker
        }),
        initial=timezone.now().date
    )

    def __init__(self, faculty=None, *args, **kwargs):
        """Filter subjects to only those taught by the logged-in faculty."""
        super().__init__(*args, **kwargs)
        if faculty:
            self.fields['subject'].queryset = Subject.objects.filter(faculty=faculty)


# ─────────────────────────────────────────────
# MAKE-UP SESSION CREATION FORM
# ─────────────────────────────────────────────
class MakeUpSessionForm(forms.ModelForm):
    """
    Faculty fills this form to schedule a make-up class.
    remedial_code is auto-generated in the view (not shown here).
    """
    class Meta:
        model  = MakeUpSession
        fields = ['subject', 'date', 'expiry_time', 'description']
        widgets = {
            'subject':     forms.Select(attrs={'class': 'form-select'}),
            'date':        forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'expiry_time': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, faculty=None, *args, **kwargs):
        """Restrict subject dropdown to faculty's own subjects."""
        super().__init__(*args, **kwargs)
        if faculty:
            self.fields['subject'].queryset = Subject.objects.filter(faculty=faculty)

    def clean_expiry_time(self):
        """Expiry time must be in the future."""
        expiry = self.cleaned_data.get('expiry_time')
        if expiry and expiry <= timezone.now():
            raise forms.ValidationError("Expiry time must be in the future.")
        return expiry


# ─────────────────────────────────────────────
# REMEDIAL CODE ENTRY FORM (for students)
# ─────────────────────────────────────────────
class RemedialCodeForm(forms.Form):
    """
    Simple form for student to enter a 6-character remedial code.
    Actual validation (expiry, duplicate use) happens in the view.
    """
    code = forms.CharField(
        max_length=10,
        label="Enter Remedial Code",
        widget=forms.TextInput(attrs={
            'class':       'form-control form-control-lg text-center text-uppercase',
            'placeholder': 'e.g. A3K9PQ',
            'maxlength':   '10',
            'style':       'letter-spacing: 4px; font-weight: bold;'
        })
    )

    def clean_code(self):
        """Normalize to uppercase."""
        return self.cleaned_data['code'].strip().upper()
