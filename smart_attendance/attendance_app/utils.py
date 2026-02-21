"""
utils.py — Helper Functions for Smart Attendance Management System
==================================================================
Contains reusable utility functions used across views:
  - Unique remedial code generator
  - Absentee detection & notification creator
  - Attendance percentage calculator
  - Attendance prediction (simple rule-based AI)
"""

import random
import string
from django.utils import timezone
from django.conf import settings
from .models import (
    Attendance, AbsenteeLog, Notification,
    MakeUpSession, StudentProfile
)

import os
import numpy as np


# ─────────────────────────────────────────────────────────
# 1. UNIQUE REMEDIAL CODE GENERATOR
# ─────────────────────────────────────────────────────────
def generate_remedial_code(length=6):
    """
    Generates a unique alphanumeric code for make-up sessions.
    Example output: 'A3K9PQ', 'XZ72BT'

    Uses uppercase letters + digits.
    Checks the database to guarantee uniqueness.
    """
    characters = string.ascii_uppercase + string.digits
    while True:
        # Generate a random 6-character code
        code = ''.join(random.choices(characters, k=length))
        # Check if this code already exists in the database
        if not MakeUpSession.objects.filter(remedial_code=code).exists():
            return code  # Unique code found, return it


# ─────────────────────────────────────────────────────────
# 2. PROCESS ABSENTEES AFTER ATTENDANCE SUBMISSION
# ─────────────────────────────────────────────────────────
def process_absentees(subject, date, absent_students, marked_by_faculty):
    """
    Called after faculty submits attendance.
    For each absent student:
      1. Create/update an AbsenteeLog entry
      2. Create an in-app Notification for the student
      3. Mark notification_sent = True

    Parameters:
        subject          : Subject model instance
        date             : date of the class (datetime.date)
        absent_students  : QuerySet or list of StudentProfile objects
        marked_by_faculty: FacultyProfile instance (who marked attendance)
    """
    for student in absent_students:
        # Step 1: Create AbsenteeLog (skip if already exists)
        log, created = AbsenteeLog.objects.get_or_create(
            student=student,
            subject=subject,
            date=date,
        )

        # Step 2: Create in-app notification for the student
        if not log.notification_sent:
            faculty_name = marked_by_faculty.user.get_full_name()
            message = (
                f"You were marked ABSENT in {subject.name} ({subject.code}) "
                f"on {date.strftime('%d %B %Y')} by {faculty_name}. "
                f"Please contact your faculty if this is incorrect."
            )
            Notification.objects.create(
                user=student.user,
                message=message,
            )
            # Mark as sent so we don't create duplicate notifications
            log.notification_sent = True
            log.save()


# ─────────────────────────────────────────────────────────
# 3. CALCULATE ATTENDANCE PERCENTAGE FOR A STUDENT
# ─────────────────────────────────────────────────────────
def get_attendance_percentage(student, subject=None):
    """
    Calculates the attendance percentage for a student.

    If subject is provided  → percentage for that specific subject
    If subject is None      → overall attendance across all subjects

    Returns a float (0.0 to 100.0), or None if no records found.

    Example:
        get_attendance_percentage(student_obj, subject_obj) → 75.0
        get_attendance_percentage(student_obj)               → 82.3
    """
    qs = Attendance.objects.filter(student=student)
    if subject:
        qs = qs.filter(subject=subject)

    total = qs.count()
    if total == 0:
        return None  # No records — show N/A in template

    present = qs.filter(status='P').count()
    percentage = (present / total) * 100
    return round(percentage, 1)


# ─────────────────────────────────────────────────────────
# 4. GET ATTENDANCE SUMMARY PER SUBJECT (for student dashboard)
# ─────────────────────────────────────────────────────────────
def get_student_subject_summary(student):
    """
    Returns a list of dictionaries with attendance stats per subject.
    Used to populate the student dashboard table and Chart.js chart.

    Example return value:
    [
        {'subject': <Subject: DS (CS301)>, 'total': 20, 'present': 17,
         'absent': 3, 'percentage': 85.0, 'status': 'Safe'},
        ...
    ]
    """
    # Get all subjects where this student has attendance records
    from .models import Subject
    subjects = Subject.objects.filter(attendances__student=student).distinct()

    summary = []
    for subject in subjects:
        total   = Attendance.objects.filter(student=student, subject=subject).count()
        present = Attendance.objects.filter(student=student, subject=subject, status='P').count()
        absent  = total - present
        pct     = round((present / total) * 100, 1) if total > 0 else 0

        # Status label: color-coded in template
        if pct >= 75:
            status = 'Safe'       # Green
        elif pct >= 60:
            status = 'Warning'    # Yellow/Orange
        else:
            status = 'Danger'     # Red

        summary.append({
            'subject':    subject,
            'total':      total,
            'present':    present,
            'absent':     absent,
            'percentage': pct,
            'status':     status,
        })
    return summary


# ─────────────────────────────────────────────────────────
# 5. ATTENDANCE PREDICTION (Simple Rule-Based AI)
# ─────────────────────────────────────────────────────────
def predict_attendance(subject):
    """
    Looks at the last 7 days of attendance for a subject.
    If average attendance > 85% → "High Attendance Expected"
    If average attendance < 60% → "Low Attendance Expected"
    Otherwise                   → "Normal Attendance Expected"

    This is a simple heuristic, NOT machine learning.
    Suitable for a B.Tech mini-project.
    """
    from datetime import timedelta
    from django.db.models import Count, Q

    today       = timezone.now().date()
    week_ago    = today - timedelta(days=7)

    # All attendance records for this subject in last 7 days
    records = Attendance.objects.filter(subject=subject, date__gte=week_ago)
    total   = records.count()

    if total == 0:
        return {"label": "No Data", "class": "secondary", "icon": "question-circle"}

    present    = records.filter(status='P').count()
    avg_pct    = (present / total) * 100

    if avg_pct >= 85:
        return {"label": f"High Attendance Expected ({avg_pct:.0f}%)", "class": "success",  "icon": "arrow-up-circle"}
    elif avg_pct < 60:
        return {"label": f"Low Attendance Expected ({avg_pct:.0f}%)",  "class": "danger",   "icon": "arrow-down-circle"}
    else:
        return {"label": f"Normal Attendance Expected ({avg_pct:.0f}%)", "class": "warning", "icon": "dash-circle"}


# ─────────────────────────────────────────────────────────
# 6. FACE RECOGNITION — OPENCV LBPH-BASED
# ─────────────────────────────────────────────────────────

# Path where the trained LBPH model is stored
FACE_MODEL_DIR  = os.path.join(settings.MEDIA_ROOT, 'face_model')
FACE_MODEL_PATH = os.path.join(FACE_MODEL_DIR, 'recognizer.yml')

# OpenCV Haar Cascade face detector (bundled with opencv-python)
_CASCADE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__import__('cv2').__file__)),
    'data', 'haarcascade_frontalface_default.xml'
)


def _get_face_detector():
    """Returns a cached OpenCV Haar cascade face detector."""
    import cv2
    detector = cv2.CascadeClassifier(_CASCADE_PATH)
    if detector.empty():
        raise RuntimeError(
            "Haar cascade XML not found. "
            "Ensure opencv-contrib-python is properly installed."
        )
    return detector


def extract_face_from_image_path(image_path, target_size=(200, 200)):
    """
    Opens an image file, detects the first face, and returns it as a
    grayscale numpy array resized to `target_size`.

    Returns:
        numpy.ndarray  — grayscale face crop, or None if no face detected.
    """
    import cv2
    img = cv2.imread(image_path)
    if img is None:
        return None

    gray     = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    detector = _get_face_detector()
    faces    = detector.detectMultiScale(
        gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60)
    )

    if len(faces) == 0:
        return None

    # Use the largest detected face
    x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
    face_crop = gray[y:y + h, x:x + w]
    return cv2.resize(face_crop, target_size)


def extract_face_from_bytes(image_bytes, target_size=(200, 200)):
    """
    Same as extract_face_from_image_path but accepts raw image bytes
    (e.g. from a webcam frame sent via AJAX as base64-decoded bytes).

    Returns:
        numpy.ndarray  — grayscale face crop, or None if no face detected.
    list of (x, y, w, h) rectangles for ALL detected faces (used for overlay).
    """
    import cv2
    nparr    = np.frombuffer(image_bytes, np.uint8)
    img      = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        return None, []

    gray     = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    detector = _get_face_detector()
    faces    = detector.detectMultiScale(
        gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60)
    )

    face_crops = []
    face_rects = []
    for (x, y, w, h) in faces:
        crop = cv2.resize(gray[y:y + h, x:x + w], target_size)
        face_crops.append(crop)
        face_rects.append({'x': int(x), 'y': int(y), 'w': int(w), 'h': int(h)})

    return face_crops, face_rects


def retrain_face_model():
    """
    Reads all StudentProfile records that have a photo.
    Auto-assigns face_label = student.id for any student missing it.
    Extracts faces from each photo, trains an LBPH model, and saves it to
    FACE_MODEL_PATH.

    Called:
      - After admin uploads a new student photo.
      - From the `train_face_model` management command.

    Returns:
        (int, list) — (number of students trained, list of error messages)
    """
    import cv2

    os.makedirs(FACE_MODEL_DIR, exist_ok=True)

    # ── Auto-fix: assign face_label to any student that has a photo but no label
    students_needing_label = StudentProfile.objects.filter(
        face_label__isnull=True
    ).exclude(photo='').filter(photo__isnull=False)
    for s in students_needing_label:
        s.face_label = s.id
        s.save(update_fields=['face_label'])

    students = StudentProfile.objects.filter(
        photo__isnull=False,
        face_label__isnull=False
    ).exclude(photo='')

    faces  = []
    labels = []
    errors = []

    for student in students:
        photo_path = os.path.join(settings.MEDIA_ROOT, str(student.photo))
        face = extract_face_from_image_path(photo_path)
        if face is None:
            errors.append(
                f"No face detected in photo for {student} (roll: {student.roll_no})"
            )
            continue
        faces.append(face)
        labels.append(student.face_label)

    if not faces:
        return 0, errors

    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.train(faces, np.array(labels))
    recognizer.save(FACE_MODEL_PATH)

    return len(faces), errors


def recognize_faces_in_frame(image_bytes, section=None, confidence_threshold=80):
    """
    Given raw JPEG/PNG bytes from a webcam frame:
      1. Detects all faces in the image.
      2. Predicts each face against the trained LBPH model.
      3. Returns student IDs whose confidence is below the threshold
         (in LBPH, lower confidence = better match).

    Parameters:
        image_bytes          : raw bytes of the image
        section              : faculty section string — only look up students
                               in this section; None = all students
        confidence_threshold : LBPH distance threshold; ≤80 is a good match

    Returns:
        dict with keys:
          'recognized_ids'  : list of student IDs recognized
          'face_rects'      : list of {'x','y','w','h'} for drawing boxes
          'error'           : error string if model not ready, else None
    """
    import cv2

    # Guard: model must exist
    if not os.path.exists(FACE_MODEL_PATH):
        return {
            'recognized_ids': [],
            'face_rects': [],
            'error': (
                'Face recognition model not trained yet. '
                'Upload student photos and run "Train Face Model".'
            )
        }

    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.read(FACE_MODEL_PATH)

    face_crops, face_rects = extract_face_from_bytes(image_bytes)

    if not face_crops:
        return {'recognized_ids': [], 'face_rects': [], 'error': None}

    # Build label→student_id map
    qs = StudentProfile.objects.filter(face_label__isnull=False)
    if section:
        qs = qs.filter(section=section)
    label_to_id = {s.face_label: s.id for s in qs}

    recognized_ids = []
    for face in face_crops:
        label, confidence = recognizer.predict(face)
        if confidence <= confidence_threshold and label in label_to_id:
            sid = label_to_id[label]
            if sid not in recognized_ids:
                recognized_ids.append(sid)

    return {
        'recognized_ids': recognized_ids,
        'face_rects':     face_rects,
        'error':          None
    }
