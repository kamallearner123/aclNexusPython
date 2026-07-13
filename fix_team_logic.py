import os

filepath = 'teams/views.py'
with open(filepath, 'r') as f:
    content = f.read()

old_my_team = """def my_team(request):
    \"\"\"
    View for developers to see their team members and chat.
    \"\"\"
    membership = request.user.team_memberships.first()
    team = membership.team if membership else None
    
    # We need to get the User objects from the TeamMember relationship
    members = []
    if team:
        # Get all users who are members of this team
        members = [m.user for m in team.members.all()]
        
    messages = team.messages.all() if team else []
    
    return render(request, 'teams/my_team.html', {
        'team': team,
        'members': members,
        'messages': messages,
    })"""

new_my_team = """def my_team(request):
    \"\"\"
    View for developers and PMs to see their team members and chat.
    \"\"\"
    teams_as_member = list(request.user.team_memberships.values_list('team', flat=True))
    teams_as_lead = list(Team.objects.filter(lead=request.user).values_list('id', flat=True))
    all_team_ids = set(teams_as_member + teams_as_lead)
    
    team_id = request.GET.get('team_id')
    if team_id and int(team_id) in all_team_ids:
        team = Team.objects.get(id=team_id)
    elif all_team_ids:
        team = Team.objects.get(id=list(all_team_ids)[0])
    else:
        team = None
        
    all_my_teams = Team.objects.filter(id__in=all_team_ids)
    
    members = []
    if team:
        members = [m.user for m in team.members.all()]
        if team.lead and team.lead not in members:
            members.append(team.lead)
            
    messages = team.messages.all() if team else []
    
    return render(request, 'teams/my_team.html', {
        'team': team,
        'all_my_teams': all_my_teams,
        'members': members,
        'messages': messages,
    })"""
content = content.replace(old_my_team, new_my_team)

old_post = """def post_team_message(request):
    membership = request.user.team_memberships.first()
    team = membership.team if membership else None
    
    if request.method == 'POST' and team:
        content = request.POST.get('content', '').strip()
        if content:
            from .models import TeamMessage
            msg = TeamMessage.objects.create(
                team=team,
                sender=request.user,
                content=content
            )
            return render(request, 'teams/partials/message.html', {'msg': msg})
    return HttpResponse(status=204)"""

new_post = """def post_team_message(request):
    team_id = request.POST.get('team_id')
    if request.method == 'POST' and team_id:
        team = get_object_or_404(Team, id=team_id)
        is_member = team.members.filter(user=request.user).exists()
        is_lead = team.lead == request.user
        
        if is_member or is_lead:
            content = request.POST.get('content', '').strip()
            if content:
                from .models import TeamMessage
                msg = TeamMessage.objects.create(
                    team=team,
                    sender=request.user,
                    content=content
                )
                return render(request, 'teams/partials/message.html', {'msg': msg})
    return HttpResponse(status=204)"""
content = content.replace(old_post, new_post)

with open(filepath, 'w') as f:
    f.write(content)
