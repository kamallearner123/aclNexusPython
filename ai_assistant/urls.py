from django.urls import path

from . import views


urlpatterns = [
    path('', views.pia_home, name='pia_home'),
    path('api/analyze/', views.pia_analyze_api, name='pia_analyze_api'),
]
