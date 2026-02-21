"""
create_sample_data.py — Management Command
==========================================
Populates the database with realistic dummy data for testing.

Run with:
    python manage.py create_sample_data

Creates:
  - 1 Admin superuser
  - 2 Faculty members
  - 10 Students
  - 4 Subjects
  - 30 days of attendance records
  - 2 Make-Up sessions
  - Sample notifications
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from attendance_app.models import (
    StudentProfile, FacultyProfile, Subject,
    Attendance, AbsenteeLog, MakeUpSession,
    MakeUpAttendance, Notification
)
from attendance_app.utils import generate_remedial_code, process_absentees
import datetime
import random


class Command(BaseCommand):
    help = 'Creates sample data for testing the attendance system'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.NOTICE('Creating sample data...'))

        # ── ADMIN ──────────────────────────────────────────
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@college.edu', 'admin123')
            self.stdout.write(self.style.SUCCESS('  ✓ Admin created (admin / admin123)'))

        # ── FACULTY ────────────────────────────────────────
        faculty_data = [
            {'username': 'prof_sharma', 'first': 'Rahul', 'last': 'Sharma',
             'email': 'sharma@college.edu', 'dept': 'CSE', 'emp_id': 'FAC001'},
            {'username': 'prof_gupta', 'first': 'Priya', 'last': 'Gupta',
             'email': 'gupta@college.edu', 'dept': 'CSE', 'emp_id': 'FAC002'},
        ]
        faculty_profiles = []
        for fd in faculty_data:
            if not User.objects.filter(username=fd['username']).exists():
                user = User.objects.create_user(
                    username=fd['username'], password='faculty123',
                    email=fd['email'], first_name=fd['first'],
                    last_name=fd['last'], is_staff=True
                )
                fp = FacultyProfile.objects.create(
                    user=user, department=fd['dept'], employee_id=fd['emp_id']
                )
                faculty_profiles.append(fp)
                self.stdout.write(f"  ✓ Faculty: {fd['username']} / faculty123")
            else:
                faculty_profiles.append(FacultyProfile.objects.get(user__username=fd['username']))

        # ── SUBJECTS ───────────────────────────────────────
        subject_data = [
            {'name': 'Data Structures', 'code': 'CS301', 'sem': 3, 'faculty': faculty_profiles[0]},
            {'name': 'Operating Systems', 'code': 'CS302', 'sem': 3, 'faculty': faculty_profiles[0]},
            {'name': 'Database Management', 'code': 'CS303', 'sem': 3, 'faculty': faculty_profiles[1]},
            {'name': 'Computer Networks', 'code': 'CS304', 'sem': 3, 'faculty': faculty_profiles[1]},
        ]
        subjects = []
        for sd in subject_data:
            subj, _ = Subject.objects.get_or_create(
                code=sd['code'],
                defaults={'name': sd['name'], 'semester': sd['sem'], 'faculty': sd['faculty']}
            )
            subjects.append(subj)
        self.stdout.write(f'  ✓ {len(subjects)} subjects created')

        # ── STUDENTS ───────────────────────────────────────
        student_names = [
            ('Arun', 'Kumar', '21CS001'), ('Bella', 'Patel', '21CS002'),
            ('Chandan', 'Singh', '21CS003'), ('Divya', 'Rao', '21CS004'),
            ('Eshan', 'Verma', '21CS005'), ('Fatima', 'Khan', '21CS006'),
            ('Gaurav', 'Mehta', '21CS007'), ('Heena', 'Shah', '21CS008'),
            ('Iqbal', 'Mirza', '21CS009'), ('Jaya', 'Nair', '21CS010'),
        ]
        student_profiles = []
        for first, last, roll in student_names:
            username = roll.lower()
            if not User.objects.filter(username=username).exists():
                user = User.objects.create_user(
                    username=username, password='student123',
                    first_name=first, last_name=last,
                    email=f'{username}@student.edu'
                )
                sp = StudentProfile.objects.create(
                    user=user, roll_no=roll,
                    department='CSE', year=3,
                    parent_email=f'parent_{username}@gmail.com'
                )
                student_profiles.append(sp)
            else:
                sp = StudentProfile.objects.get(roll_no=roll)
                student_profiles.append(sp)

        self.stdout.write(f'  ✓ {len(student_profiles)} students created (password: student123)')

        # ── ATTENDANCE RECORDS (last 30 days) ──────────────
        today = timezone.now().date()
        count = 0
        for i in range(30, 0, -1):
            date = today - datetime.timedelta(days=i)
            if date.weekday() >= 5:  # Skip weekends
                continue
            for subject in subjects:
                for student in student_profiles:
                    # Skip if already exists
                    if Attendance.objects.filter(student=student, subject=subject, date=date).exists():
                        continue
                    # 80% chance of being present (realistic)
                    status = 'P' if random.random() < 0.80 else 'A'
                    Attendance.objects.create(
                        student=student, subject=subject,
                        date=date, status=status,
                        marked_by=subject.faculty
                    )
                    count += 1

        self.stdout.write(f'  ✓ {count} attendance records created')

        # ── ABSENTEE LOGS AND NOTIFICATIONS ─────────────────
        absent_records = Attendance.objects.filter(status='A')
        notif_count = 0
        for record in absent_records[:20]:  # Create for first 20 only
            log, created = AbsenteeLog.objects.get_or_create(
                student=record.student,
                subject=record.subject,
                date=record.date,
            )
            if created and not log.notification_sent:
                Notification.objects.get_or_create(
                    user=record.student.user,
                    message=(
                        f"You were marked ABSENT in {record.subject.name} "
                        f"on {record.date.strftime('%d %B %Y')}."
                    ),
                )
                log.notification_sent = True
                log.save()
                notif_count += 1
        self.stdout.write(f'  ✓ {notif_count} absence notifications created')

        # ── MAKE-UP SESSIONS ───────────────────────────────
        if not MakeUpSession.objects.filter(subject=subjects[0]).exists():
            session = MakeUpSession.objects.create(
                subject=subjects[0],
                date=today + datetime.timedelta(days=2),
                remedial_code=generate_remedial_code(),
                expiry_time=timezone.now() + datetime.timedelta(hours=48),
                created_by=subjects[0].faculty,
                description='Covering Unit 3 topics missed due to holidays'
            )
            self.stdout.write(f'  ✓ Make-Up session created | Code: {session.remedial_code}')

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('═' * 60))
        self.stdout.write(self.style.SUCCESS('  SAMPLE DATA CREATED SUCCESSFULLY!'))
        self.stdout.write(self.style.SUCCESS('═' * 60))
        self.stdout.write(self.style.WARNING('  LOGIN CREDENTIALS:'))
        self.stdout.write('  Admin    → admin / admin123')
        self.stdout.write('  Faculty  → prof_sharma / faculty123')
        self.stdout.write('  Faculty  → prof_gupta / faculty123')
        self.stdout.write('  Students → 21cs001 / student123 (through 21cs010)')
        self.stdout.write(self.style.SUCCESS('═' * 60))
