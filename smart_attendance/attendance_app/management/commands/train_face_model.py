"""
Management Command: train_face_model
======================================
Trains (or retrains) the OpenCV LBPH face recognizer from all student
photos stored in the database.

Usage:
    python manage.py train_face_model
    python manage.py train_face_model --verbosity 2

What it does:
  1. Queries every StudentProfile that has a photo uploaded.
  2. Extracts the face from each photo using a Haar cascade detector.
  3. Trains an LBPH face recognizer with (face_image, student.id) pairs.
  4. Saves the model to  media/face_model/recognizer.yml

Run this command after:
  - Bulk-importing student photos via Django admin
  - Manually adding photos to existing students
"""

from django.core.management.base import BaseCommand
from attendance_app.utils import retrain_face_model, FACE_MODEL_PATH
from attendance_app.models import StudentProfile


class Command(BaseCommand):
    help = 'Train the OpenCV LBPH face recognition model from all student photos.'

    def handle(self, *args, **options):
        total = StudentProfile.objects.count()

        # Count students with photo (regardless of face_label)
        with_photo = StudentProfile.objects.filter(
            photo__isnull=False
        ).exclude(photo='').count()

        # Count students missing face_label but having a photo (fixable)
        missing_label = StudentProfile.objects.filter(
            photo__isnull=False, face_label__isnull=True
        ).exclude(photo='').count()

        self.stdout.write(f"\n  Total students       : {total}")
        self.stdout.write(f"  Students w/ photo    : {with_photo}")
        self.stdout.write(f"  Missing face_label   : {missing_label}")
        self.stdout.write("")

        if missing_label > 0:
            self.stdout.write(
                self.style.WARNING(
                    f"  Auto-fixing {missing_label} student(s) with missing face_label..."
                )
            )

        if with_photo == 0:
            self.stdout.write(
                self.style.WARNING(
                    "  No student photos found.\n"
                    "  Upload photos via Admin Panel → Add Student.\n"
                )
            )
            return

        self.stdout.write("  Training LBPH face model...")
        trained_count, errors = retrain_face_model()

        if errors:
            self.stdout.write(self.style.WARNING(f"\n  Warnings ({len(errors)}):"))
            for e in errors:
                self.stdout.write(f"    ⚠  {e}")

        if trained_count > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\n  ✔ Model trained on {trained_count} student(s).\n"
                    f"    Saved to: {FACE_MODEL_PATH}\n"
                )
            )
        else:
            self.stdout.write(
                self.style.ERROR(
                    "\n  ✘ No faces could be detected in any photo.\n"
                    "  Make sure photos are clear, frontal-face images.\n"
                )
            )
