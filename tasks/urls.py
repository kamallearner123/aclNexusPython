from django.urls import path
from . import views

urlpatterns = [
    path('kanban/', views.kanban_board, name='tasks_kanban'),
    path('calendar/', views.user_calendar, name='user_calendar'),
    path('new/', views.task_create, name='task_create'),
    path('<int:pk>/', views.task_detail, name='task_detail'),
    path('<int:pk>/deactivate/', views.task_deactivate, name='task_deactivate'),
    path('<int:pk>/edit/', views.task_update, name='task_update'),
    path('update-status/', views.update_task_status, name='update_task_status'),
    path('<int:pk>/ai-action/', views.task_ai_action, name='task_ai_action'),
]
