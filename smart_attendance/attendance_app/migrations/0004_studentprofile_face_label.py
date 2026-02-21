"""
Migration: Add face_label field to StudentProfile
Used by OpenCV LBPH face recognizer to map integer label → student.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('attendance_app', '0003_add_section_to_student_profile'),
    ]

    operations = [
        migrations.AddField(
            model_name='studentprofile',
            name='face_label',
            field=models.PositiveIntegerField(
                blank=True,
                null=True,
                help_text='Auto-assigned integer label used in OpenCV LBPH face model training.'
            ),
        ),
    ]
