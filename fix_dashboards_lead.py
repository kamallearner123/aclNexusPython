import os

filepath = 'core/views.py'
with open(filepath, 'r') as f:
    content = f.read()

# Update pm_dashboard
old_pm = """def pm_dashboard(request):
    user = request.user
    user_teams = list(user.team_memberships.values_list('team', flat=True))
    if user.team_id:
        user_teams.append(user.team_id)"""

new_pm = """def pm_dashboard(request):
    user = request.user
    from teams.models import Team
    user_teams = list(user.team_memberships.values_list('team', flat=True))
    if user.team_id:
        user_teams.append(user.team_id)
    teams_as_lead = list(Team.objects.filter(lead=user).values_list('id', flat=True))
    user_teams.extend(teams_as_lead)"""
content = content.replace(old_pm, new_pm)

# Update architect_dashboard
old_arch = """def architect_dashboard(request):
    user = request.user
    user_teams = list(user.team_memberships.values_list('team', flat=True))
    if user.team_id:
        user_teams.append(user.team_id)"""

new_arch = """def architect_dashboard(request):
    user = request.user
    from teams.models import Team
    user_teams = list(user.team_memberships.values_list('team', flat=True))
    if user.team_id:
        user_teams.append(user.team_id)
    teams_as_lead = list(Team.objects.filter(lead=user).values_list('id', flat=True))
    user_teams.extend(teams_as_lead)"""
content = content.replace(old_arch, new_arch)

# Update engineer_dashboard
old_eng = """def engineer_dashboard(request):
    user = request.user
    
    user_teams = list(user.team_memberships.values_list('team', flat=True))
    if user.team_id:
        user_teams.append(user.team_id)"""

new_eng = """def engineer_dashboard(request):
    user = request.user
    from teams.models import Team
    
    user_teams = list(user.team_memberships.values_list('team', flat=True))
    if user.team_id:
        user_teams.append(user.team_id)
    teams_as_lead = list(Team.objects.filter(lead=user).values_list('id', flat=True))
    user_teams.extend(teams_as_lead)"""
content = content.replace(old_eng, new_eng)

with open(filepath, 'w') as f:
    f.write(content)
