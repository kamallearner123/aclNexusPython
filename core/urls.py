from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing_page, name='landing_page'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('register/', views.register, name='register'),
    path('system-admin/', views.system_admin_dashboard, name='system_admin_dashboard'),
    path('system-admin/employees/new/', views.employee_create, name='employee_create'),
    path('system-admin/employees/<int:pk>/delete/', views.employee_delete, name='employee_delete'),
    path('attachments/upload/', views.attachment_upload, name='attachment_upload'),
    path('attachments/<int:pk>/delete/', views.attachment_delete, name='attachment_delete'),
]
