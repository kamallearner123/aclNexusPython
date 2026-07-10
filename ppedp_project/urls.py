from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('tasks/', include('tasks.urls')),
    path('risks/', include('risks.urls')),
    path('issues/', include('issues.urls')),
    path('projects/', include('projects.urls')),
    path('teams/', include('teams.urls')),
    path('pia/', include('ai_assistant.urls')),
    path('accounts/', include('django.contrib.auth.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
