from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.risk_register, name='risks_register'),
    path('new/', views.risk_create, name='risk_create'),
]
