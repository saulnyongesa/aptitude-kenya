from django.urls import path
from . import views

urlpatterns = [
    # The Homepage
    path('', views.index, name='index'),
    
    # The AJAX Contact Form Endpoint
    path('send-message/', views.send_message, name='send_message'),
    
    # Placeholder for other links in your index.html (Classrooms, Exams, etc)
    # path('classrooms/', views.classroom_list, name='classroom_list'),
]