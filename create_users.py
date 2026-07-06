import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ppedp_project.settings')
django.setup()

from core.models import User, Role

# Ensure roles exist
role_architect, _ = Role.objects.get_or_create(name='Architect')
role_developer, _ = Role.objects.get_or_create(name='Developer')
role_tester, _ = Role.objects.get_or_create(name='Tester')

users_data = {
    'roopa@aptcomputinglabs.com': ('roopa', 'roopa123', role_developer),
    'robin@aptcomputinglabs.com': ('robin', 'robin123', role_developer),
    'thanseef@aptcomputinglabs.com': ('thanseef', 'thanseef123', role_developer),
    'kamal@aptcomputinglabs.com': ('kamal', 'kamal123', role_architect),
    'supriya@aptcomputinglabs.com': ('supriya', 'supriya123', role_tester),
}

for email, (first_name, password, role) in users_data.items():
    user, created = User.objects.get_or_create(email=email)
    user.first_name = first_name
    if created:
        user.set_password(password)
    user.save()
    user.roles.add(role)
    action = "Created" if created else "Updated"
    print(f"{action} user {email} with role {role.name}")

print("Done configuring users.")
