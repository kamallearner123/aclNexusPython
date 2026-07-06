from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from projects.models import Project
from tasks.models import Task
from issues.models import Issue
from risks.models import Risk
from teams.models import Team
from django.contrib.contenttypes.models import ContentType
from .models import User, Attachment
from .forms import CustomUserCreationForm, EmployeeCreationForm

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
    projects = Project.objects.filter(owner=request.user)
    context = {
        'role_title': 'Project Manager Dashboard',
        'active_projects': projects.filter(status='ACTIVE').count(),
        'open_tasks': Task.objects.filter(project__in=projects).exclude(status='COMPLETED').count(),
        'high_risks': Risk.objects.filter(project__in=projects, risk_level__in=['HIGH', 'CRITICAL']).count(),
        'open_issues': Issue.objects.filter(project__in=projects, status__in=['OPEN', 'IN_PROGRESS']).count(),
        'projects': projects,
    }
    return render(request, 'core/dashboards/pm.html', context)

@login_required
@user_passes_test(is_architect)
def architect_dashboard(request):
    team = request.user.team
    team_users = team.team_users.all() if team else []
    
    if team:
        team_tasks = Task.objects.filter(assignee__in=team_users).exclude(status='COMPLETED')
    else:
        team_tasks = Task.objects.none()
        
    my_tasks = Task.objects.filter(assignee=request.user).exclude(status='COMPLETED')
    
    context = {
        'role_title': 'Architect Dashboard',
        'team': team,
        'team_tasks_open': team_tasks.count(),
        'my_tasks': my_tasks,
    }
    return render(request, 'core/dashboards/architect.html', context)

@login_required
@user_passes_test(is_engineer)
def engineer_dashboard(request):
    my_tasks = Task.objects.filter(assignee=request.user)
    my_projects = Project.objects.filter(tasks__assignee=request.user).distinct()
    context = {
        'role_title': 'Engineer Dashboard',
        'open_tasks': my_tasks.exclude(status='COMPLETED').count(),
        'my_projects_count': my_projects.count(),
        'my_tasks': my_tasks.order_by('-created_at')[:10],
        'my_projects': my_projects,
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
def employee_delete(request, pk):
    if request.method == 'POST':
        user = User.objects.get(pk=pk)
        if user != request.user: # Prevent self-deletion
            user.delete()
    return redirect('system_admin_dashboard')

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
