import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ppedp_project.settings')
django.setup()

from projects.models import Project
from core.models import User
from teams.models import Team, TeamMember

user = User.objects.filter(email__icontains='dhanush').first()
if user:
    print("User found:", user.email)
    
    # Assign the first project to Cyber Security team
    project = Project.objects.first()
    team = Team.objects.filter(name='Cyber Security').first()
    if project and team:
        print(f"Assigning {team.name} to {project.name}...")
        project.teams.add(team)
    
    projects = Project.objects.filter(teams__members__user=user).distinct()
    print("Projects for user (teams__members__user):", projects)
    
    # Test teams__core_users=user as well
    projects2 = Project.objects.filter(teams__core_users=user).distinct()
    print("Projects for user (teams__core_users):", projects2)
    
else:
    print("User dhanush not found")
