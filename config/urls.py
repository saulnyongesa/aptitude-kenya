from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from core import views

urlpatterns = [
    # Django Admin
    path('admin/', admin.site.urls),
    
    # Include your app's URLs
    path('', include('core.urls')), 
    
    # Authentication system (Login/Register)
    path('auth/', views.auth_view, name='auth_page'),
    path('auth/logout/', views.logout_view, name='logout'),

]

# Serving static/media files during development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)