from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing_page, name='landing_page'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/pm/', views.pm_dashboard, name='pm_dashboard'),
    path('dashboard/architect/', views.architect_dashboard, name='architect_dashboard'),
    path('dashboard/engineer/', views.engineer_dashboard, name='engineer_dashboard'),
    path('register/', views.register, name='register'),
    path('system-admin/', views.system_admin_dashboard, name='system_admin_dashboard'),
    path('system-admin/employees/new/', views.employee_create, name='employee_create'),
    path('system-admin/employees/<int:pk>/edit/', views.employee_edit, name='employee_edit'),
    path('system-admin/employees/<int:pk>/delete/', views.employee_delete, name='employee_delete'),
    path('attachments/upload/', views.attachment_upload, name='attachment_upload'),
    path('attachments/<int:pk>/delete/', views.attachment_delete, name='attachment_delete'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    path('notes/', views.notes_dashboard, name='notes_dashboard'),
    path('notes/topics/new/', views.note_topic_create, name='note_topic_create'),
    path('notes/new/', views.note_create, name='note_create'),
    path('notes/<int:pk>/', views.note_detail, name='note_detail'),
    path('notes/<int:pk>/edit/', views.note_edit, name='note_edit'),
    path('notes/<int:pk>/delete/', views.note_delete, name='note_delete'),
]
