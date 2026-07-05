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

# Create your views here.
