import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ppedp_project.settings')
django.setup()

from core.models import User, Role

role_pm, _ = Role.objects.get_or_create(name='Project Manager')

email = 'dhanush@aptcomputinglabs.com'
first_name = 'Dhanush'
password = 'dhanush123'

user, created = User.objects.get_or_create(email=email)
user.first_name = first_name
if created:
    user.set_password(password)
user.save()
user.roles.add(role_pm)

action = "Created" if created else "Updated"
print(f"{action} user {email} with role {role_pm.name}")
