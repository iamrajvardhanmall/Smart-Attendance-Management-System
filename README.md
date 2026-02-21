# Smart Attendance Management System

> **Developed by [Rajvardhan Mall](https://github.com/iamrajvardhanmall)**
> [![GitHub](https://img.shields.io/badge/GitHub-iamrajvardhanmall-181717?logo=github)](https://github.com/iamrajvardhanmall)
> [![LinkedIn](https://img.shields.io/badge/LinkedIn-rajvardhanmall-0A66C2?logo=linkedin)](https://www.linkedin.com/in/rajvardhanmall/)

A Django-based web application for managing student attendance in an academic institution. Faculty can mark attendance manually or automatically using **webcam face recognition**. Admins manage users and view analytics. Students track their own attendance and receive absence notifications.

---

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Developer](#developer)
- [Project Structure](#project-structure)
- [Setup & Installation](#setup--installation)
- [User Roles](#user-roles)
- [Face Recognition Setup](#face-recognition-setup)
- [Usage Guide](#usage-guide)
- [Database Schema](#database-schema)
- [Screenshots](#screenshots)

---

## Features

### Admin
- Create student and faculty accounts (no self-registration)
- Upload student photos for face recognition training
- View system-wide analytics — attendance trends, charts, subject stats
- Re-train face recognition model from the browser

### Faculty
- Mark attendance manually via checkbox table
- **Auto-mark attendance using live webcam face recognition**
- View attendance reports per subject with per-student percentages
- Filter absentee logs by subject and date range
- Schedule make-up / remedial sessions with auto-generated codes
- Attendance prediction badge per subject (last 7 days trend)

### Student
- View attendance percentage per subject with Safe / Warning / Danger status
- See detailed attendance history (regular + make-up)
- Enter remedial code to mark make-up class attendance
- Receive in-app notifications for absences and scheduled make-up sessions

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Django 6.0.2 (Python) |
| Database | SQLite 3 |
| Face Recognition | OpenCV 4.13 — LBPH Face Recognizer |
| Face Detection | OpenCV Haar Cascade |
| Frontend | Bootstrap 5.3 + Bootstrap Icons |
| Charts | Chart.js |
| Image Handling | Pillow 12.1.1 |

---

## Project Structure

```
Smart-Attendance-Management-System/
├── attendance/                    # Python virtual environment
│   └── Scripts/activate
├── smart_attendance/              # Django project root
│   ├── manage.py
│   ├── requirements.txt
│   ├── db.sqlite3
│   ├── media/
│   │   ├── student_photos/        # Uploaded student face photos
│   │   └── face_model/
│   │       └── recognizer.yml     # Trained LBPH face model
│   ├── static/
│   │   ├── css/style.css
│   │   └── js/
│   │       ├── attendance.js      # Global JS utilities
│   │       └── camera.js          # Webcam face recognition module
│   ├── templates/
│   │   ├── base.html
│   │   ├── home.html
│   │   ├── admin_dashboard/
│   │   ├── faculty/
│   │   ├── student/
│   │   └── registration/
│   ├── attendance_app/            # Main Django app
│   │   ├── models.py              # 8 database models
│   │   ├── views.py               # All view functions
│   │   ├── urls.py                # URL routing
│   │   ├── forms.py               # Form classes
│   │   ├── utils.py               # Face recognition + helpers
│   │   ├── decorators.py          # Role-based access control
│   │   ├── context_processors.py  # Global notification count
│   │   ├── templatetags/
│   │   │   └── attendance_tags.py
│   │   ├── migrations/
│   │   └── management/commands/
│   │       └── train_face_model.py
│   └── smart_attendance/
│       ├── settings.py
│       └── urls.py
```

---

## Setup & Installation

### 1. Clone the repository

```bash
git clone https://github.com/your-username/Smart-Attendance-Management-System.git
cd Smart-Attendance-Management-System
```

### 2. Create and activate virtual environment

```bash
# Create venv
python -m venv attendance

# Activate (Windows)
attendance\Scripts\activate

# Activate (Linux/Mac)
source attendance/bin/activate
```

### 3. Install dependencies

```bash
cd smart_attendance
pip install -r requirements.txt
```

### 4. Apply database migrations

```bash
python manage.py migrate
```

### 5. Create a superuser (Admin account)

```bash
python manage.py createsuperuser
```

### 6. Run the development server

```bash
python manage.py runserver
```

Visit: **http://127.0.0.1:8000/**

---

## User Roles

### Admin (Superuser)
- Login at: `http://127.0.0.1:8000/login/`
- Username = superuser username set during `createsuperuser`
- Access Analytics, Add Student, Add Faculty

### Faculty
- Login ID = **5-character Faculty ID** (e.g. `FAC01`) — assigned by admin
- Admin creates faculty at: `http://127.0.0.1:8000/admin-panel/create-faculty/`

### Student
- Login ID = **8-digit Registration Number** (e.g. `12345678`) — assigned by admin
- Admin creates student at: `http://127.0.0.1:8000/admin-panel/create-student/`
- No self-registration is allowed for any role

---

## Face Recognition Setup

The system uses **OpenCV LBPH (Local Binary Pattern Histogram)** face recognizer.  
No internet or external API is needed — everything runs locally.

### Step 1 — Upload student photo

When creating a student (Admin Panel → Add Student), upload a clear frontal face photo (`.jpg` / `.png`).  
The model retrains automatically after each upload.

### Step 2 — Train the model (for existing students or bulk uploads)

```bash
python manage.py train_face_model
```

Expected output:
```
  Total students       : 5
  Students w/ photo    : 5
  Missing face_label   : 0
  Training LBPH face model...
  ✔ Model trained on 5 student(s).
    Saved to: ...media/face_model/recognizer.yml
```

### Step 3 — Use webcam on Mark Attendance page

1. Faculty opens **Mark Attendance** → selects subject + date → loads student list
2. The **Face Recognition panel** appears → click **Start Camera**
3. Webcam opens and scans every 2 seconds
4. Matched students are **auto-checked as Present** with a yellow flash
5. Faculty reviews and submits

### Photo guidelines for best accuracy

| Requirement | Detail |
|---|---|
| Format | `.jpg` or `.png` |
| Face | Single person, looking directly at camera |
| Lighting | Well-lit, no heavy shadows |
| Resolution | At least 200×200 px |
| Expression | Neutral preferred |

---

## Usage Guide

### Marking Attendance (Faculty)

1. Log in as faculty
2. **Mark Attendance** → select subject + date → click **Load Students**
3. *(Optional)* Click **Start Camera** for auto face recognition
4. Manually check/uncheck students as needed
5. Click **Save Attendance** → absent students are auto-notified

### Scheduling a Make-Up Session (Faculty)

1. **Make-Up → Schedule Make-Up**
2. Select subject, date, expiry time, description
3. A unique 6-character **Remedial Code** is auto-generated (e.g. `A3K9PQ`)
4. All previously-absent students receive an in-app notification with the code

### Entering Remedial Code (Student)

1. Log in as student
2. **Remedial Code** in navbar → enter the code given by faculty
3. System validates: code exists → not expired → not already used → marks attendance

### Viewing Analytics (Admin only)

- Go to `http://127.0.0.1:8000/analytics/`
- Total Students, Faculty, Subjects, Records
- Pie chart: Present vs Absent
- Line chart: 30-day attendance trend
- Bar chart: Subject-wise attendance %

---

## Database Schema

```
User (built-in)
 ├── FacultyProfile  (1:1)
 ├── StudentProfile  (1:1)
 │    └── face_label  ← integer label for LBPH recognition
 └── Notification    (1:many)

Subject  ← belongs to FacultyProfile
 └── Attendance  ← student + subject + date + P/A status
      └── AbsenteeLog  ← auto-created on absence

MakeUpSession  ← created by faculty with remedial_code
 └── MakeUpAttendance  ← created when student enters code
```

---

## Key URLs

| URL | Description | Access |
|---|---|---|
| `/` | Home / dashboard redirect | All |
| `/login/` | Login page | Public |
| `/admin-panel/create-student/` | Create student account | Admin |
| `/admin-panel/create-faculty/` | Create faculty account | Admin |
| `/faculty/dashboard/` | Faculty dashboard | Faculty |
| `/faculty/mark-attendance/` | Mark attendance + webcam | Faculty |
| `/faculty/attendance-report/` | Attendance report | Faculty |
| `/faculty/absentees/` | Absentee log | Faculty |
| `/faculty/makeup/create/` | Schedule make-up session | Faculty |
| `/student/dashboard/` | Student dashboard | Student |
| `/student/my-attendance/` | Attendance history | Student |
| `/student/remedial-code/` | Enter remedial code | Student |
| `/student/notifications/` | In-app notifications | Student |
| `/analytics/` | System-wide analytics | Admin only |
| `/api/recognize-faces/` | AJAX face recognition endpoint | Faculty |
| `/api/retrain-face-model/` | Retrain LBPH model | Admin |

---

## Developer

| | |
|---|---|
| **Name** | Rajvardhan Mall |
| **GitHub** | [@iamrajvardhanmall](https://github.com/iamrajvardhanmall) |
| **LinkedIn** | [rajvardhanmall](https://www.linkedin.com/in/rajvardhanmall/) |

---

## License

MIT License

Copyright (c) 2026 Rajvardhan Mall

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
