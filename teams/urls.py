from django.urls import path
from . import views

urlpatterns = [
    path('new/', views.team_create, name='team_create'),
    path('<int:pk>/', views.team_detail, name='team_detail'),
    path('<int:pk>/delete/', views.team_delete, name='team_delete'),
]
