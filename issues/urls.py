from django.urls import path
from . import views

urlpatterns = [
    path('tracker/', views.issue_tracker, name='issue_tracker'),
    path('new/', views.issue_create, name='issue_create'),
    path('<int:pk>/', views.issue_detail, name='issue_detail'),
    path('<int:pk>/update/', views.issue_update, name='issue_update'),
]
