from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth.views import LoginView
from django.views.decorators.cache import never_cache

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/login/', never_cache(LoginView.as_view(template_name='registration/login.html')), name='login'),
    path('', include('core.urls')),
    path('tasks/', include('tasks.urls')),
    path('risks/', include('risks.urls')),
    path('issues/', include('issues.urls')),
    path('projects/', include('projects.urls')),
    path('teams/', include('teams.urls')),
    path('pia/', include('ai_assistant.urls')),
    path('lms/', include('lms.urls')),
    path('accounts/', include('django.contrib.auth.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
