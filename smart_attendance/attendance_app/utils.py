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

def generate_remedial_code(length=6):
    characters = string.ascii_uppercase + string.digits
    while True:
        code = ''.join(random.choices(characters, k=length))
        if not MakeUpSession.objects.filter(remedial_code=code).exists():
            return code  

def process_absentees(subject, date, absent_students, marked_by_faculty):
    for student in absent_students:
        log, created = AbsenteeLog.objects.get_or_create(
            student=student,
            subject=subject,
            date=date,
        )

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
            
            log.notification_sent = True
            log.save()

def get_attendance_percentage(student, subject=None):
    qs = Attendance.objects.filter(student=student)
    if subject:
        qs = qs.filter(subject=subject)
    total = qs.count()
    if total == 0:
        return None  
    present = qs.filter(status='P').count()
    percentage = (present / total) * 100
    return round(percentage, 1)
def get_student_subject_summary(student):
    from .models import Subject
    subjects = Subject.objects.filter(attendances__student=student).distinct()
    summary = []
    for subject in subjects:
        total   = Attendance.objects.filter(student=student, subject=subject).count()
        present = Attendance.objects.filter(student=student, subject=subject, status='P').count()
        absent  = total - present
        pct     = round((present / total) * 100, 1) if total > 0 else 0
        if pct >= 75:
            status = 'Safe'       
        elif pct >= 60:
            status = 'Warning'
        else:
            status = 'Danger'     
        summary.append({
            'subject':    subject,
            'total':      total,
            'present':    present,
            'absent':     absent,
            'percentage': pct,
            'status':     status,
        })
    return summary

def predict_attendance(subject):
    from datetime import timedelta
    from django.db.models import Count, Q

    today       = timezone.now().date()
    week_ago    = today - timedelta(days=7)
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
FACE_MODEL_DIR  = os.path.join(settings.MEDIA_ROOT, 'face_model')
FACE_MODEL_PATH = os.path.join(FACE_MODEL_DIR, 'recognizer.yml')

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
    x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
    face_crop = gray[y:y + h, x:x + w]
    return cv2.resize(face_crop, target_size)


def extract_face_from_bytes(image_bytes, target_size=(200, 200)):
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
    import cv2
    os.makedirs(FACE_MODEL_DIR, exist_ok=True)

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
    import cv2
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
