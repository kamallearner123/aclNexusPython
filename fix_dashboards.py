import os

filepath = 'core/views.py'
with open(filepath, 'r') as f:
    content = f.read()

# Update pm_dashboard
old_pm = """def pm_dashboard(request):
    user = request.user
    q_proj = Q(owner=user) | Q(created_by=user)
    if user.team:
        q_proj |= Q(team=user.team)
    projects = Project.objects.filter(q_proj).distinct()"""

new_pm = """def pm_dashboard(request):
    user = request.user
    user_teams = list(user.team_memberships.values_list('team', flat=True))
    if user.team_id:
        user_teams.append(user.team_id)
        
    q_proj = Q(owner=user) | Q(created_by=user)
    if user_teams:
        q_proj |= Q(team__in=user_teams)
    projects = Project.objects.filter(q_proj).distinct()"""
content = content.replace(old_pm, new_pm)

# Update architect_dashboard
old_arch = """def architect_dashboard(request):
    team = request.user.team
    team_users = team.team_users.all() if team else []
    
    if team:
        team_tasks = Task.objects.filter(Q(assignee__in=team_users) | Q(project__team=team)).exclude(status='COMPLETED').distinct()
    else:
        team_tasks = Task.objects.none()"""

new_arch = """def architect_dashboard(request):
    user = request.user
    user_teams = list(user.team_memberships.values_list('team', flat=True))
    if user.team_id:
        user_teams.append(user.team_id)
        
    team = user.team
    team_users = team.team_users.all() if team else []
    
    if user_teams:
        team_tasks = Task.objects.filter(Q(assignee__in=team_users) | Q(project__team__in=user_teams)).exclude(status='COMPLETED').distinct()
    else:
        team_tasks = Task.objects.none()"""
content = content.replace(old_arch, new_arch)

# Update engineer_dashboard
old_eng = """def engineer_dashboard(request):
    user = request.user
    
    q_task = Q(assignee=user) | Q(created_by=user)
    if user.team:
        q_task |= Q(project__team=user.team)
    my_tasks = Task.objects.filter(q_task).distinct()
    
    q_proj = Q(tasks__assignee=user) | Q(owner=user) | Q(created_by=user)
    if user.team:
        q_proj |= Q(team=user.team)
    my_projects = Project.objects.filter(q_proj).distinct()"""

new_eng = """def engineer_dashboard(request):
    user = request.user
    
    user_teams = list(user.team_memberships.values_list('team', flat=True))
    if user.team_id:
        user_teams.append(user.team_id)
    
    q_task = Q(assignee=user) | Q(created_by=user)
    if user_teams:
        q_task |= Q(project__team__in=user_teams)
    my_tasks = Task.objects.filter(q_task).distinct()
    
    q_proj = Q(tasks__assignee=user) | Q(owner=user) | Q(created_by=user)
    if user_teams:
        q_proj |= Q(team__in=user_teams)
    my_projects = Project.objects.filter(q_proj).distinct()"""
content = content.replace(old_eng, new_eng)

with open(filepath, 'w') as f:
    f.write(content)
