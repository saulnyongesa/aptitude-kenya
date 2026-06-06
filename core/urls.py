from django.urls import path
from . import views

urlpatterns = [
    # The Homepage
    path('', views.index, name='index'),
    path('portal/', views.portal_landing, name='portal_landing'),
    
    # The AJAX Contact Form Endpoint
    path('send-message/', views.send_message, name='send_message'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/admin/', views.admin_dashboard, name='admin_dashboard'),
    path('dashboard/tutor/', views.tutor_dashboard, name='tutor_dashboard'),
    path('dashboard/tutor/classrooms/<int:classroom_id>/', views.classroom_detail, name='classroom_detail'),
    path('dashboard/tutor/classrooms/<int:classroom_id>/edit/', views.classroom_edit, name='classroom_edit'),
    path('dashboard/tutor/classrooms/<int:classroom_id>/archive/', views.classroom_archive, name='classroom_archive'),
    path('dashboard/tutor/students/<int:student_id>/reset-credentials/', views.reset_student_credentials_view, name='reset_student_credentials'),
    path('dashboard/student/', views.student_dashboard, name='student_dashboard'),
    
    # Placeholder for other links in your index.html (Classrooms, Exams, etc)
    # path('classrooms/', views.classroom_list, name='classroom_list'),
]
