from django.urls import path
from . import views

urlpatterns = [
    path('', views.project_list, name='project_list'),
    path('new/', views.project_create, name='project_create'),
    path('<int:pk>/', views.project_detail, name='project_detail'),
    path('<int:pk>/print/', views.project_print, name='project_print'),
    path('<int:pk>/edit/', views.project_update, name='project_update'),
    path('<int:pk>/delete/', views.project_delete, name='project_delete'),
    path('<int:pk>/process-board/', views.automotive_process_board, name='automotive_process_board'),
    path('<int:project_id>/requirements/new/', views.requirement_create, name='requirement_create'),
    path('<int:project_id>/requirements/bulk/', views.requirement_bulk_create, name='requirement_bulk_create'),
    path('requirements/<int:pk>/', views.requirement_detail, name='requirement_detail'),
    path('requirements/<int:pk>/deactivate/', views.requirement_deactivate, name='requirement_deactivate'),
    path('requirements/<int:pk>/edit/', views.requirement_update, name='requirement_update'),
    path('requirements/<int:pk>/convert/', views.requirement_convert_to_task, name='requirement_convert_to_task'),
]
