from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import Team, TeamMember
from .forms import TeamForm, TeamMemberForm

def is_admin(user):
    return user.is_staff or user.is_superuser

@login_required
@user_passes_test(is_admin)
def team_create(request):
    if request.method == 'POST':
        form = TeamForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('system_admin_dashboard')
    else:
        form = TeamForm()
    return render(request, 'teams/form.html', {'form': form})

@login_required
@user_passes_test(is_admin)
def team_delete(request, pk):
    if request.method == 'POST':
        team = get_object_or_404(Team, pk=pk)
        team.delete()
    return redirect('system_admin_dashboard')

@login_required
@user_passes_test(is_admin)
def team_detail(request, pk):
    team = get_object_or_404(Team, pk=pk)
    
    if request.method == 'POST':
        if 'add_member' in request.POST:
            form = TeamMemberForm(request.POST, team=team)
            if form.is_valid():
                member = form.save(commit=False)
                member.team = team
                member.save()
                return redirect('team_detail', pk=team.pk)
        elif 'remove_member' in request.POST:
            member_id = request.POST.get('member_id')
            TeamMember.objects.filter(pk=member_id, team=team).delete()
            return redirect('team_detail', pk=team.pk)
            
    form = TeamMemberForm(team=team)
    return render(request, 'teams/detail.html', {'team': team, 'form': form})

@login_required
def my_team(request):
    """
    View for developers to see their team members and chat.
    """
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
    })

from django.http import HttpResponse

@login_required
def post_team_message(request):
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
    return HttpResponse(status=204)
