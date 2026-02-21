
from django.urls import path
from . import views

urlpatterns = [
    path('',        views.home_view,   name='home'),
    path('login/',  views.login_view,  name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('admin-panel/create-student/', views.admin_create_student_view, name='admin_create_student'),
    path('admin-panel/create-faculty/', views.admin_create_faculty_view, name='admin_create_faculty'),
    path('faculty/dashboard/',          views.faculty_dashboard_view,      name='faculty_dashboard'),
    path('faculty/mark-attendance/',    views.mark_attendance_view,        name='mark_attendance'),
    path('faculty/attendance-report/',  views.attendance_report_view,      name='attendance_report'),
    path('faculty/absentees/',          views.absentee_list_view,          name='absentee_list'),
    path('faculty/makeup/create/',      views.create_makeup_session_view,  name='create_makeup'),
    path('faculty/makeup/list/',        views.makeup_sessions_list_view,   name='makeup_sessions_list'),
    path('student/dashboard/',          views.student_dashboard_view,      name='student_dashboard'),
    path('student/my-attendance/',      views.my_attendance_view,          name='my_attendance'),
    path('student/remedial-code/',      views.enter_remedial_code_view,    name='enter_remedial'),
    path('student/notifications/',      views.notifications_view,          name='notifications'),
    path('analytics/',                  views.admin_analytics_view,        name='analytics'),
    path('api/recognize-faces/',        views.recognize_faces_api,         name='recognize_faces_api'),
    # Admin-triggered face model retraining
    path('api/retrain-face-model/',     views.retrain_face_model_view,     name='retrain_face_model'),
]
