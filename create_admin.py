import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ppedp_project.settings')
django.setup()

from core.models import User

if not User.objects.filter(email='admin@admin.com').exists():
    user = User.objects.create_superuser('admin@admin.com', 'admin123')
    print("Created superuser: admin@admin.com / admin123")
else:
    user = User.objects.get(email='admin@admin.com')
    user.set_password('admin123')
    user.save()
    print("Reset password for superuser: admin@admin.com / admin123")
