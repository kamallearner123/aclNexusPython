from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.risks_register, name='risks_register'),
    path('new/', views.risk_create, name='risk_create'),

    path('<int:pk>/', views.risk_detail, name='risk_detail'),
    path('<int:pk>/edit/', views.risk_update, name='risk_update'),
    path('delete/<int:id>/', views.risk_delete, name='risk_delete'),
]