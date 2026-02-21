from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Q
from django.http import JsonResponse

import datetime

from .models import (
    StudentProfile, FacultyProfile, Subject,
    Attendance, AbsenteeLog, MakeUpSession,
    MakeUpAttendance, Notification
)
from .forms import (
    LoginForm, AdminStudentCreationForm, AdminFacultyCreationForm,
    AttendanceFilterForm, MakeUpSessionForm, RemedialCodeForm
)
from .decorators import faculty_required, student_required
from .utils import (
    generate_remedial_code, process_absentees,
    get_student_subject_summary, predict_attendance,
    retrain_face_model, recognize_faces_in_frame
)
def home_view(request):
    if not request.user.is_authenticated:
        return render(request, 'home.html')

    if hasattr(request.user, 'faculty_profile'):
        return redirect('faculty_dashboard')
    elif hasattr(request.user, 'student_profile'):
        return redirect('student_dashboard')
    else:
        # Superuser or admin
        return redirect('/admin/')


def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    form = LoginForm(request, data=request.POST or None)

    if request.method == 'POST':
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Welcome back, {user.first_name}!")
            return redirect('home')
        else:
            messages.error(request, "Invalid username or password.")

    return render(request, 'registration/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out successfully.")
    return redirect('login')


@login_required
def admin_create_student_view(request):
    if not request.user.is_staff:
        messages.error(request, "Access denied. Admin only.")
        return redirect('home')
    form = AdminStudentCreationForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        reg_no = form.cleaned_data['registration_number']  # 8-digit number
        user = User.objects.create_user(
            username   = reg_no,
            password   = form.cleaned_data['password1'],
            first_name = form.cleaned_data['first_name'],
            last_name  = form.cleaned_data['last_name'],
            email      = form.cleaned_data.get('email', ''),
        )
        student = StudentProfile.objects.create(
            user         = user,
            roll_no      = reg_no,
            department   = form.cleaned_data['department'],
            year         = form.cleaned_data['year'],
            parent_email = form.cleaned_data.get('parent_email', ''),
            section      = form.cleaned_data.get('section', '') or None,
        )
        student.face_label = student.id
        photo = form.cleaned_data.get('photo')
        if photo:
            student.photo = photo
        student.save()

        # Auto-retrain face model if a photo was provided
        if photo:
            trained_count, errs = retrain_face_model()
            if errs:
                messages.warning(
                    request,
                    f"Student created but face encoding issue: {errs[0]}"
                )
            else:
                messages.success(
                    request,
                    f"Student account created & face model updated! "
                    f"({trained_count} students trained)  "
                    f"Name: {user.get_full_name()} | Login ID: {reg_no}"
                )
        else:
            messages.success(
                request,
                f"Student account created! "
                f"Name: {user.get_full_name()} | Login ID: {reg_no}  "
                f"(No photo — upload one later to enable face recognition.)"
            )
        return redirect('admin_create_student')

    # List existing students for display on the same page
    students = StudentProfile.objects.select_related('user').order_by('roll_no')
    return render(request, 'admin_dashboard/create_student.html', {
        'form': form,
        'students': students,
    })


@login_required # Login Required
def admin_create_faculty_view(request):
    if not request.user.is_staff:
        messages.error(request, "Access denied. Admin only.")
        return redirect('home')

    form = AdminFacultyCreationForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        fid = form.cleaned_data['faculty_id']  

        user = User.objects.create_user(
            username   = fid,
            password   = form.cleaned_data['password1'],
            first_name = form.cleaned_data['first_name'],
            last_name  = form.cleaned_data['last_name'],
            email      = form.cleaned_data.get('email', ''),
            is_staff   = True,  
        )
        FacultyProfile.objects.create(
            user        = user,
            department  = form.cleaned_data['department'],
            employee_id = fid,
            section     = form.cleaned_data.get('section', '') or None,
        )
        messages.success(
            request,
            f"Faculty account created! "
            f"Name: Prof. {user.get_full_name()} | Login ID: {fid}"
        )
        return redirect('admin_create_faculty')
    faculty_list = FacultyProfile.objects.select_related('user').order_by('employee_id')
    return render(request, 'admin_dashboard/create_faculty.html', {
        'form': form,
        'faculty_list': faculty_list,
    })

@faculty_required
def faculty_dashboard_view(request):
    faculty  = request.user.faculty_profile
    subjects = Subject.objects.filter(faculty=faculty)
    today    = timezone.now().date()
    today_attendance = Attendance.objects.filter(
        subject__in=subjects,
        date=today
    ).count()
    recent_absentees = AbsenteeLog.objects.filter(
        subject__in=subjects,
        date__gte=today - datetime.timedelta(days=7)
    ).order_by('-date')[:10]
    upcoming_makeups = MakeUpSession.objects.filter(
        created_by=faculty,
        expiry_time__gt=timezone.now()
    ).order_by('date')[:5]
    predictions = {s.id: predict_attendance(s) for s in subjects}
    context = {
        'faculty':          faculty,
        'subjects':         subjects,
        'today_attendance': today_attendance,
        'recent_absentees': recent_absentees,
        'upcoming_makeups': upcoming_makeups,
        'predictions':      predictions,
        'today':            today,
    }
    return render(request, 'faculty/dashboard.html', context)


@faculty_required
def mark_attendance_view(request):
    faculty = request.user.faculty_profile
    filter_form = AttendanceFilterForm(faculty=faculty, data=request.GET or None)
    students     = []
    existing_map = {}  
    subject      = None
    selected_date = None
    if filter_form.is_valid():
        subject       = filter_form.cleaned_data['subject']
        selected_date = filter_form.cleaned_data['date']
        if faculty.section:
            students = StudentProfile.objects.filter(
                section=faculty.section
            ).order_by('roll_no')
        else:
            students = StudentProfile.objects.all().order_by('roll_no')
        existing = Attendance.objects.filter(subject=subject, date=selected_date)
        existing_map = {a.student_id: a.status for a in existing}
    if request.method == 'POST':
        subject_id    = request.POST.get('subject_id')
        selected_date = request.POST.get('date')
        present_ids   = request.POST.getlist('present_students')  
        subject       = get_object_or_404(Subject, id=subject_id, faculty=faculty)
        selected_date = datetime.date.fromisoformat(selected_date)
        if faculty.section:
            all_students = StudentProfile.objects.filter(section=faculty.section)
        else:
            all_students = StudentProfile.objects.all()
        absent_students = []
        for student in all_students:
            status = 'P' if str(student.id) in present_ids else 'A'
            Attendance.objects.update_or_create(
                student=student,
                subject=subject,
                date=selected_date,
                defaults={'status': status, 'marked_by': faculty}
            )
            if status == 'A':
                absent_students.append(student)

        process_absentees(subject, selected_date, absent_students, faculty)

        msg = (
            f"Attendance saved for {subject.name} on {selected_date}. "
            f"{len(present_ids)} present, {len(absent_students)} absent."
        )
        messages.success(request, msg)
        return redirect('faculty_dashboard')

    context = {
        'filter_form':   filter_form,
        'students':      students,
        'existing_map':  existing_map,
        'subject':       subject,
        'selected_date': selected_date,
    }
    return render(request, 'faculty/mark_attendance.html', context)


@faculty_required
def attendance_report_view(request):
    faculty  = request.user.faculty_profile
    subjects = Subject.objects.filter(faculty=faculty)
    selected_subject = None
    report_data      = []
    date_list        = [
    subject_id = request.GET.get('subject')
    if subject_id:
        selected_subject = get_object_or_404(Subject, id=subject_id, faculty=faculty)
        date_list = (
            Attendance.objects
            .filter(subject=selected_subject)
            .values_list('date', flat=True)
            .distinct()
            .order_by('date')
        )
        if faculty.section:
            students = StudentProfile.objects.filter(section=faculty.section).order_by('roll_no')
        else:
            students = StudentProfile.objects.all().order_by('roll_no')
        for student in students:
            row = {'student': student, 'statuses': [], 'present': 0, 'total': 0, 'pct': 0}
            for date in date_list:
                try:
                    att = Attendance.objects.get(student=student, subject=selected_subject, date=date)
                    row['statuses'].append(att.status)
                    row['total'] += 1
                    if att.status == 'P':
                        row['present'] += 1
                except Attendance.DoesNotExist:
                    row['statuses'].append('-')  
            if row['total'] > 0:
                row['pct'] = round((row['present'] / row['total']) * 100, 1)
            report_data.append(row)
    context = {
        'subjects':         subjects,
        'selected_subject': selected_subject,
        'report_data':      report_data,
        'date_list':        date_list,
    }
    return render(request, 'faculty/attendance_report.html', context)


@faculty_required
def absentee_list_view(request):
    faculty  = request.user.faculty_profile
    subjects = Subject.objects.filter(faculty=faculty)
    subject_id = request.GET.get('subject')
    from_date  = request.GET.get('from_date')
    to_date    = request.GET.get('to_date')
    logs = AbsenteeLog.objects.filter(subject__in=subjects).order_by('-date')
    if subject_id:
        logs = logs.filter(subject_id=subject_id)
    if from_date:
        logs = logs.filter(date__gte=from_date)
    if to_date:
        logs = logs.filter(date__lte=to_date)
    context = {
        'logs':     logs,
        'subjects': subjects,
        'filters':  {'subject': subject_id, 'from_date': from_date, 'to_date': to_date},
    }
    return render(request, 'faculty/absentee_list.html', context)


@faculty_required
def create_makeup_session_view(request):
    faculty = request.user.faculty_profile
    form    = MakeUpSessionForm(faculty=faculty, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        session               = form.save(commit=False)
        session.created_by    = faculty
        session.remedial_code = generate_remedial_code()  
        session.save()
        absent_students = StudentProfile.objects.filter(
            absentee_logs__subject=session.subject
        ).distinct()

        for student in absent_students:
            Notification.objects.create(
                user=student.user,
                message=(
                    f"A Make-Up class has been scheduled for {session.subject.name} "
                    f"on {session.date.strftime('%d %B %Y')}. "
                    f"Use remedial code: {session.remedial_code} (expires: {session.expiry_time.strftime('%d %b %Y %H:%M')})"
                )
            )

        messages.success(
            request,
            f"Make-Up session created! Remedial Code: {session.remedial_code}"
        )
        return redirect('makeup_sessions_list')

    context = {'form': form, 'faculty': faculty}
    return render(request, 'faculty/create_makeup.html', context)


@faculty_required
def makeup_sessions_list_view(request):
    """Lists all make-up sessions created by this faculty."""
    faculty  = request.user.faculty_profile
    sessions = MakeUpSession.objects.filter(created_by=faculty).order_by('-date')
    context  = {'sessions': sessions}
    return render(request, 'faculty/makeup_sessions.html', context)

@student_required
def student_dashboard_view(request):
    student = request.user.student_profile
    summary = get_student_subject_summary(student)  
    makeup_records = MakeUpAttendance.objects.filter(student=student).order_by('-marked_at')[:5]
    chart_labels = [item['subject'].name for item in summary]
    chart_data   = [item['percentage'] for item in summary]
    context = {
        'student':         student,
        'summary':         summary,
        'makeup_records':  makeup_records,
        'chart_labels':    chart_labels,
        'chart_data':      chart_data,
    }
    return render(request, 'student/dashboard.html', context)
@student_required
def my_attendance_view(request):
    student = request.user.student_profile
    subject_id = request.GET.get('subject')
    regular_records = Attendance.objects.filter(student=student).order_by('-date')
    if subject_id:
        regular_records = regular_records.filter(subject_id=subject_id)
    makeup_records = MakeUpAttendance.objects.filter(student=student).order_by('-marked_at')
    my_subjects = Subject.objects.filter(attendances__student=student).distinct()
    context = {
        'regular_records': regular_records,
        'makeup_records':  makeup_records,
        'my_subjects':     my_subjects,
        'selected_subject': subject_id,
    }
    return render(request, 'student/my_attendance.html', context)

@student_required
def enter_remedial_code_view(request):
    student = request.user.student_profile
    form    = RemedialCodeForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        code = form.cleaned_data['code']
        try:
            session = MakeUpSession.objects.get(remedial_code=code)
        except MakeUpSession.DoesNotExist:
            messages.error(request, f"Invalid code: '{code}' not found.")
            return render(request, 'student/enter_remedial.html', {'form': form})
        if not session.is_active():
            messages.error(request, f"Code '{code}' has expired. Please contact your faculty.")
            return render(request, 'student/enter_remedial.html', {'form': form})
        if MakeUpAttendance.objects.filter(student=student, session=session).exists():
            messages.warning(request, f"You have already marked attendance for this make-up session.")
            return render(request, 'student/enter_remedial.html', {'form': form})
        MakeUpAttendance.objects.create(student=student, session=session)
        Notification.objects.create(
            user=student.user,
            message=(
                f"Make-Up attendance marked for {session.subject.name} "
                f"(Make-Up class on {session.date.strftime('%d %B %Y')}). Well done!"
            )
        )

        messages.success(
            request,
            f"Make-Up attendance recorded for {session.subject.name}. "
            f"Class date: {session.date.strftime('%d %B %Y')}"
        )
        return redirect('student_dashboard')

    return render(request, 'student/enter_remedial.html', {'form': form})


@student_required
def notifications_view(request):
    notifications = Notification.objects.filter(user=request.user).order_by('-timestamp')
    notifications.filter(is_read=False).update(is_read=True)
    if hasattr(request.user, 'student_profile'):
        AbsenteeLog.objects.filter(
            student=request.user.student_profile,
            acknowledged=False
        ).update(acknowledged=True)

    context = {'notifications': notifications}
    return render(request, 'student/notifications.html', context)

@login_required
def admin_analytics_view(request):
    if not request.user.is_staff or hasattr(request.user, 'faculty_profile'):
        messages.error(request, "Admin access only.")
        return redirect('home')
    today     = timezone.now().date()
    month_ago = today - datetime.timedelta(days=30)
    total_students  = StudentProfile.objects.count()
    total_faculty   = FacultyProfile.objects.count()
    total_subjects  = Subject.objects.count()
    total_records   = Attendance.objects.count()
    present_count = Attendance.objects.filter(status='P').count()
    absent_count  = Attendance.objects.filter(status='A').count()
    trend_data = []
    for i in range(30, 0, -1):
        d      = today - datetime.timedelta(days=i)
        p      = Attendance.objects.filter(date=d, status='P').count()
        a      = Attendance.objects.filter(date=d, status='A').count()
        trend_data.append({'date': d.strftime('%d/%m'), 'present': p, 'absent': a})

    subjects     = Subject.objects.all()
    subject_stats = []
    for s in subjects:
        total = Attendance.objects.filter(subject=s).count()
        if total > 0:
            pct = round(Attendance.objects.filter(subject=s, status='P').count() / total * 100, 1)
            subject_stats.append({'name': s.code, 'percentage': pct})

    context = {
        'total_students':  total_students,
        'total_faculty':   total_faculty,
        'total_subjects':  total_subjects,
        'total_records':   total_records,
        'present_count':   present_count,
        'absent_count':    absent_count,
        'trend_data':      trend_data,
        'subject_stats':   subject_stats,
    }
    return render(request, 'admin_dashboard/analytics.html', context)

import base64
@faculty_required
def recognize_faces_api(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    image_data = request.POST.get('image', '')
    if not image_data:
        return JsonResponse({'error': 'No image data received.'}, status=400)
    if ',' in image_data:
        image_data = image_data.split(',', 1)[1]
    try:
        image_bytes = base64.b64decode(image_data)
    except Exception:
        return JsonResponse({'error': 'Invalid base64 image.'}, status=400)
    section = request.user.faculty_profile.section or None
    result = recognize_faces_in_frame(image_bytes, section=section)
    return JsonResponse(result)


@login_required
def retrain_face_model_view(request):
    if not request.user.is_staff:
        return JsonResponse({'error': 'Admin only.'}, status=403)

    trained_count, errors = retrain_face_model()
    return JsonResponse({'trained': trained_count, 'errors': errors})
