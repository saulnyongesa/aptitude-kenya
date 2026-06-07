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
    path('dashboard/tutor/assessments/', views.assessment_list, name='assessment_list'),
    path('dashboard/tutor/assessments/new/', views.assessment_create, name='assessment_create'),
    path('dashboard/tutor/assessments/<int:exam_id>/', views.assessment_detail, name='assessment_detail'),
    path('dashboard/tutor/assessments/<int:exam_id>/edit/', views.assessment_edit, name='assessment_edit'),
    path('dashboard/tutor/assessments/<int:exam_id>/sections/add/', views.assessment_add_section, name='assessment_add_section'),
    path('dashboard/tutor/assessments/<int:exam_id>/questions/add/', views.assessment_add_question, name='assessment_add_question'),
    path('dashboard/tutor/assessments/<int:exam_id>/questions/import/', views.assessment_import_questions, name='assessment_import_questions'),
    path('dashboard/tutor/assessments/<int:exam_id>/questions/from-bank/', views.assessment_add_from_bank, name='assessment_add_from_bank'),
    path('dashboard/tutor/assessments/<int:exam_id>/publish/', views.assessment_publish, name='assessment_publish'),
    path('dashboard/tutor/billing/', views.billing_overview, name='billing_overview'),
    path('dashboard/tutor/billing/subscriptions/', views.subscription_plans, name='subscription_plans'),
    path('dashboard/tutor/billing/subscriptions/<int:plan_id>/start/', views.start_subscription, name='start_subscription'),
    path('dashboard/tutor/billing/invoices/<int:invoice_id>/', views.invoice_detail, name='invoice_detail'),
    path('dashboard/tutor/billing/invoices/<int:invoice_id>/mpesa/', views.invoice_start_mpesa, name='invoice_start_mpesa'),
    path('dashboard/tutor/billing/invoices/<int:invoice_id>/dev-confirm/', views.invoice_dev_confirm, name='invoice_dev_confirm'),
    path('payments/mpesa/stk-callback/', views.mpesa_stk_callback, name='mpesa_stk_callback'),
    path('payments/mpesa/c2b-confirmation/', views.mpesa_c2b_confirmation, name='mpesa_c2b_confirmation'),
    path('dashboard/tutor/students/<int:student_id>/reset-credentials/', views.reset_student_credentials_view, name='reset_student_credentials'),
    path('dashboard/student/', views.student_dashboard, name='student_dashboard'),
    path('dashboard/student/assessments/<int:exam_id>/start/', views.student_assessment_start, name='student_assessment_start'),
    path('dashboard/student/attempts/<int:submission_id>/', views.student_assessment_take, name='student_assessment_take'),
    path('dashboard/student/attempts/<int:submission_id>/result/', views.student_assessment_result, name='student_assessment_result'),
    path('dashboard/student/attempts/<int:submission_id>/proctor-violation/', views.student_proctor_violation, name='student_proctor_violation'),
    
    # Placeholder for other links in your index.html (Classrooms, Exams, etc)
    # path('classrooms/', views.classroom_list, name='classroom_list'),
]
