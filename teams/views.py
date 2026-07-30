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
    View for developers and PMs to see their team members and chat.
    """
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

    # unread message count
    from .models import DirectMessage

    for member in members:
     member.unread_count = DirectMessage.objects.filter(
        sender=member,
        recipient=request.user,
        is_read=False
    ).count()

     print(
        "Member:",
        member.email,
        "Unread:",
        member.unread_count
    )
            
    messages = team.messages.all() if team else []
    
    return render(request, 'teams/my_team.html', {
        'team': team,
        'all_my_teams': all_my_teams,
        'members': members,
        'messages': messages,
    })

from django.http import HttpResponse

@login_required
def post_team_message(request):
    print("===== POST TEAM MESSAGE =====")
    print(request.POST)

    team_id = request.POST.get('team_id')

    if request.method == 'POST' and team_id:
        team = get_object_or_404(Team, id=team_id)

        content = request.POST.get('content', '').strip()
        print("CONTENT REPR =", repr(request.POST.get('content')))

        print("TEAM:", team)
        print("USER:", request.user)
        print("CONTENT:", content)

        from .models import TeamMessage
        print("POST DATA =", request.POST)
        print("CONTENT =", request.POST.get("content"))

        msg = TeamMessage.objects.create(
            team=team,
            sender=request.user,
            content=content
        )

        return render(
            request,
            'teams/partials/message.html',
            {'msg': msg}
        )

    return HttpResponse(status=204)

from django.db.models import Q
from core.models import User

@login_required
def direct_chat_popup(request, user_id):
    other_user = get_object_or_404(User, pk=user_id)
    from .models import DirectMessage
    
    messages = DirectMessage.objects.filter(
        Q(sender=request.user, recipient=other_user) | 
        Q(sender=other_user, recipient=request.user)
    ).order_by('created_at')
    
    # Mark messages from other user as read
    DirectMessage.objects.filter(sender=other_user, recipient=request.user, is_read=False).update(is_read=True)
    
    return render(request, 'teams/partials/direct_chat_popup.html', {
        'other_user': other_user,
        'messages': messages,
    })

@login_required
def post_direct_message(request, user_id):

    from .models import DirectMessage

    other_user = get_object_or_404(User, pk=user_id)

    print("=========== DIRECT MESSAGE ===========")
    print(request.POST)

    if request.method == "POST":

        content = request.POST.get("content", "").strip()

        print("CONTENT =", repr(content))

        if content:

            msg = DirectMessage.objects.create(
                sender=request.user,
                recipient=other_user,
                content=content
            )

            return render(
                request,
                "teams/partials/message.html",
                {
                    "msg": msg,
                    "is_direct": True
                }
            )

    return HttpResponse(status=204)