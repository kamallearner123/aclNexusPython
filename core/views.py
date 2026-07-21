from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from projects.models import Project
from tasks.models import Task
from issues.models import Issue
from risks.models import Risk
from teams.models import Team
from django.contrib.contenttypes.models import ContentType
from .models import User, Attachment
from .forms import CustomUserCreationForm, EmployeeCreationForm, EmployeeEditForm
from .utils import get_daily_ai_news

@login_required
def landing_page(request):
    """
    Global App Hub Landing Page.
    """
    return render(request, 'core/landing.html')

def is_pm(user):
    return user.roles.filter(name='Project Manager').exists()

def is_architect(user):
    return user.roles.filter(name='Architect').exists()

def is_engineer(user):
    return user.roles.filter(name__in=['Developer', 'Tester', 'Customer Engineer']).exists()

@login_required
def dashboard(request):
    """
    Main dashboard view that redirects based on role.
    """
    # Admin will now see the stats dashboard natively

    if is_pm(request.user):
        return redirect('pm_dashboard')
    elif is_architect(request.user):
        return redirect('architect_dashboard')
    elif is_engineer(request.user):
        return redirect('engineer_dashboard')
    
    context = {
        'active_projects': Project.objects.filter(status='ACTIVE').count(),
        'completed_tasks': Task.objects.filter(status='COMPLETED').count(),
        'open_issues': Issue.objects.filter(status__in=['OPEN', 'IN_PROGRESS']).count(),
        'high_risks': Risk.objects.filter(risk_level__in=['HIGH', 'CRITICAL']).count(),
    }
    return render(request, 'core/dashboard.html', context)

@login_required
@user_passes_test(is_pm)
def pm_dashboard(request):
    user = request.user
    from teams.models import Team
    user_teams = list(user.team_memberships.values_list('team', flat=True))
    teams_as_lead = list(Team.objects.filter(lead=user).values_list('id', flat=True))
    user_teams.extend(teams_as_lead)
        
    q_proj = Q(owner=user) | Q(created_by=user)
    if user_teams:
        q_proj |= Q(teams__in=user_teams)
    projects = Project.objects.filter(q_proj).distinct()
    
    context = {
        'role_title': 'Project Manager Dashboard',
        'active_projects': projects.filter(status='ACTIVE').count(),
        'open_tasks': Task.objects.filter(project__in=projects).exclude(status='COMPLETED').count(),
        'high_risks': Risk.objects.filter(project__in=projects, risk_level__in=['HIGH', 'CRITICAL']).count(),
        'open_issues': Issue.objects.filter(project__in=projects, status__in=['OPEN', 'IN_PROGRESS']).count(),
        'projects': projects,
        'ai_news': get_daily_ai_news(request.user),
    }
    return render(request, 'core/dashboards/pm.html', context)

from django.db.models import Q

@login_required
@user_passes_test(is_architect)
def architect_dashboard(request):
    user = request.user
    from teams.models import Team
    user_teams = list(user.team_memberships.values_list('team', flat=True))
    teams_as_lead = list(Team.objects.filter(lead=user).values_list('id', flat=True))
    user_teams.extend(teams_as_lead)
        
    team = user.teams.first()
    team_users = team.core_users.all() if team else []
    
    if user_teams:
        team_tasks = Task.objects.filter(Q(assignee__in=team_users) | Q(project__teams__in=user_teams)).exclude(status='COMPLETED').distinct()
    else:
        team_tasks = Task.objects.none()
        
    my_tasks = Task.objects.filter(Q(assignee=request.user) | Q(created_by=request.user)).exclude(status='COMPLETED').distinct()
    
    context = {
        'role_title': 'Architect Dashboard',
        'team': team,
        'team_tasks_open': team_tasks.count(),
        'my_tasks': my_tasks,
        'ai_news': get_daily_ai_news(request.user),
    }
    return render(request, 'core/dashboards/architect.html', context)

from django.db.models import Count

@login_required
@user_passes_test(is_engineer)
def engineer_dashboard(request):
    user = request.user
    from teams.models import Team
    
    user_teams = list(user.team_memberships.values_list('team', flat=True))
    teams_as_lead = list(Team.objects.filter(lead=user).values_list('id', flat=True))
    user_teams.extend(teams_as_lead)
    
    q_task = Q(assignee=user) | Q(created_by=user)
    if user_teams:
        q_task |= Q(project__teams__in=user_teams)
    my_tasks = Task.objects.filter(q_task).distinct()
    
    q_proj = Q(tasks__assignee=user) | Q(owner=user) | Q(created_by=user)
    if user_teams:
        q_proj |= Q(teams__in=user_teams)
    my_projects = Project.objects.filter(q_proj).distinct()
    
    task_statuses = my_tasks.values('status').annotate(count=Count('status'))
    status_labels = []
    status_counts = []
    status_dict = dict(Task.STATUS_CHOICES)
    for item in task_statuses:
        status_labels.append(status_dict.get(item['status'], item['status']))
        status_counts.append(item['count'])
        
    import json
    
    context = {
        'role_title': 'Engineer Dashboard',
        'open_tasks': my_tasks.exclude(status='COMPLETED').count(),
        'my_projects_count': my_projects.count(),
        'my_tasks': my_tasks.order_by('-created_at')[:10],
        'my_projects': my_projects,
        'task_status_labels': json.dumps(status_labels),
        'task_status_counts': json.dumps(status_counts),
        'ai_news': get_daily_ai_news(request.user),
    }
    return render(request, 'core/dashboards/engineer.html', context)

def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = CustomUserCreationForm()
    return render(request, 'registration/register.html', {'form': form})

# Admin specific views
def is_admin(user):
    return user.is_staff or user.is_superuser

@login_required
@user_passes_test(is_admin)
def system_admin_dashboard(request):
    """
    Modern Admin Dashboard for managing Employees, Teams, and Projects.
    """
    users = User.objects.all().order_by('-created_at')
    teams = Team.objects.all().order_by('-created_at')
    
    # We no longer need projects here since it has its own dedicated tab view.
    
    return render(request, 'core/system_admin.html', {
        'users': users,
        'teams': teams,
        'tab': request.GET.get('tab', 'all'),
    })

@login_required
@user_passes_test(is_admin)
def employee_create(request):
    if request.method == 'POST':
        form = EmployeeCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('system_admin_dashboard')
    else:
        form = EmployeeCreationForm()
    return render(request, 'core/employee_form.html', {'form': form})

@login_required
@user_passes_test(is_admin)
def employee_edit(request, pk):
    employee = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        form = EmployeeEditForm(request.POST, instance=employee)
        if form.is_valid():
            form.save()
            return redirect('/system-admin/?tab=engineers')
    else:
        form = EmployeeEditForm(instance=employee)
    return render(request, 'core/employee_form.html', {'form': form, 'is_edit': True, 'employee': employee})

@login_required
@user_passes_test(is_admin)
def employee_toggle_status(request, pk):
    if request.method == 'POST':
        user = User.objects.get(pk=pk)
        if user != request.user: # Prevent self-toggling
            user.is_active = not user.is_active
            user.save()
    return redirect('/system-admin/?tab=engineers')

@login_required
def attachment_upload(request):
    if request.method == 'POST' and request.FILES.get('file'):
        file = request.FILES['file']
        model_name = request.POST.get('model_name')
        object_id = request.POST.get('object_id')
        
        # Get content type
        content_type = ContentType.objects.get(app_label__in=['projects', 'tasks', 'issues'], model=model_name.lower())
        
        Attachment.objects.create(
            file=file,
            filename=file.name,
            uploaded_by=request.user,
            content_type=content_type,
            object_id=object_id
        )
        
    return redirect(request.META.get('HTTP_REFERER', 'dashboard'))

@login_required
def attachment_delete(request, pk):
    if request.method == 'POST':
        from django.shortcuts import get_object_or_404
        attachment = get_object_or_404(Attachment, pk=pk)
        attachment.delete()
    return redirect(request.META.get('HTTP_REFERER', 'dashboard'))

@login_required
def profile_edit(request):
    from .forms import ProfileEditForm
    if request.method == 'POST':
        form = ProfileEditForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect(request.META.get('HTTP_REFERER', 'dashboard'))
    else:
        form = ProfileEditForm(instance=request.user)
    return render(request, 'core/profile_edit.html', {'form': form})

from django.shortcuts import get_object_or_404
from .models import NoteTopic, Note
from .forms import NoteTopicForm, NoteForm

@login_required
def notes_dashboard(request):
    topics = NoteTopic.objects.filter(user=request.user)
    selected_topic_id = request.GET.get('topic')
    if selected_topic_id:
        notes = Note.objects.filter(user=request.user, topic_id=selected_topic_id)
    else:
        notes = Note.objects.filter(user=request.user)
    
    return render(request, 'core/notes/dashboard.html', {
        'topics': topics,
        'notes': notes,
        'selected_topic_id': int(selected_topic_id) if selected_topic_id else None
    })

@login_required
def note_topic_create(request):
    if request.method == 'POST':
        form = NoteTopicForm(request.POST)
        if form.is_valid():
            topic = form.save(commit=False)
            topic.user = request.user
            topic.save()
            return redirect('notes_dashboard')
    else:
        form = NoteTopicForm()
    return render(request, 'core/notes/topic_form.html', {'form': form})

@login_required
def note_create(request):
    if request.method == 'POST':
        form = NoteForm(request.POST, request.FILES)
        form.fields['topic'].queryset = NoteTopic.objects.filter(user=request.user)
        if form.is_valid():
            note = form.save(commit=False)
            note.user = request.user
            note.save()
            
            # Handle attachments
            from django.contrib.contenttypes.models import ContentType
            content_type = ContentType.objects.get_for_model(Note)
            for f in request.FILES.getlist('attachments'):
                Attachment.objects.create(
                    file=f,
                    filename=f.name,
                    uploaded_by=request.user,
                    content_type=content_type,
                    object_id=note.pk
                )
            return redirect('notes_dashboard')
    else:
        form = NoteForm()
        form.fields['topic'].queryset = NoteTopic.objects.filter(user=request.user)
        
    return render(request, 'core/notes/note_form.html', {'form': form})

@login_required
def note_detail(request, pk):
    note = get_object_or_404(Note, pk=pk, user=request.user)
    
    if request.method == 'POST':
        content = request.POST.get('entry_content')
        if content and content.strip() and content != '<p><br></p>':
            from .models import NoteEntry
            NoteEntry.objects.create(note=note, user=request.user, content=content)
            return redirect('note_detail', pk=pk)
            
    return render(request, 'core/notes/note_detail.html', {'note': note})

@login_required
def note_edit(request, pk):
    note = get_object_or_404(Note, pk=pk, user=request.user)
    if request.method == 'POST':
        form = NoteForm(request.POST, request.FILES, instance=note)
        form.fields['topic'].queryset = NoteTopic.objects.filter(user=request.user)
        if form.is_valid():
            note = form.save()
            
            # Handle attachments
            from django.contrib.contenttypes.models import ContentType
            content_type = ContentType.objects.get_for_model(Note)
            for f in request.FILES.getlist('attachments'):
                Attachment.objects.create(
                    file=f,
                    filename=f.name,
                    uploaded_by=request.user,
                    content_type=content_type,
                    object_id=note.pk
                )
            return redirect('note_detail', pk=note.pk)
    else:
        form = NoteForm(instance=note)
        form.fields['topic'].queryset = NoteTopic.objects.filter(user=request.user)
        
    return render(request, 'core/notes/note_form.html', {'form': form, 'is_edit': True, 'note': note})

@login_required
def note_delete(request, pk):
    note = get_object_or_404(Note, pk=pk, user=request.user)
    if request.method == 'POST':
        note.delete()
        return redirect('notes_dashboard')
    # Use detail page for deletion or a new template. We will just redirect if GET for safety or render confirm.
    # To keep it simple without another template, we'll just allow POST to delete.
    return redirect('note_detail', pk=pk)
