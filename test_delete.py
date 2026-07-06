import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ppedp_project.settings')
django.setup()

from projects.models import Project
p = Project.objects.first()
if p:
    print(f"Deleting {p.pk}")
    p.delete()
    print("Deleted successfully!")
else:
    print("No project found.")
