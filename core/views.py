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

@login_required
def dashboard(request):
    """
    Main dashboard view.
    """
    context = {
        'active_projects': Project.objects.filter(status='ACTIVE').count(),
        'completed_tasks': Task.objects.filter(status='COMPLETED').count(),
        'open_issues': Issue.objects.filter(status__in=['OPEN', 'IN_PROGRESS']).count(),
        'high_risks': Risk.objects.filter(risk_level__in=['HIGH', 'CRITICAL']).count(),
    }
    return render(request, 'core/dashboard.html', context)

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
    projects = Project.objects.all().order_by('-created_at')
    
    return render(request, 'core/system_admin.html', {
        'users': users,
        'teams': teams,
        'projects': projects,
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
