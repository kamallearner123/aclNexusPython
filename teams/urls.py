from django.urls import path
from . import views

urlpatterns = [
    path('new/', views.team_create, name='team_create'),
    path('my-team/', views.my_team, name='my_team'),
    path('my-team/post-message/', views.post_team_message, name='post_team_message'),
    path('<int:pk>/', views.team_detail, name='team_detail'),
    path('<int:pk>/delete/', views.team_delete, name='team_delete'),
]
